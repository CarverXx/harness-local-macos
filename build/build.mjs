// Rebuild the desktop main from the matching source. Reuse the verified release's unchanged renderer,
// native modules and runtime. Never write to the stock application or its user profile.
import * as asar from '@electron/asar'
import { build } from 'esbuild'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import {
  existsSync,
  readFileSync,
  cpSync,
  mkdirSync,
  rmSync,
  mkdtempSync,
  statSync,
  renameSync,
} from 'node:fs'
import { basename, dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Readable } from 'node:stream'
import { tmpdir } from 'node:os'
import assert from 'node:assert/strict'

const project = fileURLToPath(new URL('../', import.meta.url))
const [sourceDir, target, runtime] = process.argv.slice(2)
if (!sourceDir || !runtime) throw Error('Run build/build.sh with the upstream checkout, output path and signed runtime')
const root = resolve(sourceDir)
const upstream = process.env.LOCAL_HARNESS_UPSTREAM
const base = '9c2670d3bce5275e0d1610272958121af87787bb'
if (!upstream) throw Error('Missing pinned upstream checkout')
const input = resolve(runtime)
if (!target || !basename(target).endsWith('.app') || existsSync(target))
  throw Error('Supply a fresh destination .app path')
const cmd = (file, args) =>
  execFileSync(file, args, { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 })
cmd('codesign', ['--verify', '--deep', '--strict', input])
cmd('codesign', [
  '--verify',
  '-R=anchor apple generic and certificate leaf[subject.OU] = "NAN929V4UM"',
  input,
])
const archive = join(input, 'Contents/Resources/app.asar')
const archiveBytes = readFileSync(archive)
const raw = asar.getRawHeader(archive)
const info = JSON.parse(asar.extractFile(archive, 'package.json'))
const version = JSON.parse(
  readFileSync(join(root, 'apps/desktop/package.json')),
).version
assert.equal(info.version, version)
const replacements = new Map()
function replace(path, bytes) {
  assert(asar.statFile(archive, path).size > 0)
  replacements.set(path, Buffer.from(bytes))
}
const dependencyIndex = raw.header.files.node_modules.files
const runtimePackages = raw.header.files.dsh.files.node_modules.files
const output = await build({
  entryPoints: [join(root, 'apps/desktop/src/main.ts')],
  bundle: true,
  write: false,
  format: 'esm',
  platform: 'node',
  target: 'es2024',
  define: { 'process.env.DSH_CLIENT_VERSION': JSON.stringify(version) },
  plugins: [
    {
      name: 'release-dependencies',
      setup(builder) {
        builder.onResolve({ filter: /^[@a-zA-Z]/ }, ({ path }) => {
          if (path.startsWith('node:') || path === 'electron')
            return { path, external: true }
          const names = path.split('/')
          const pkg = names[0].startsWith('@')
            ? names.splice(0, 2)
            : names.splice(0, 1)
          const existsIn = (tree) =>
            pkg.length === 1 ? tree[pkg[0]] : tree[pkg[0]]?.files?.[pkg[1]]
          if (path === 'mime')
            return { path: fileURLToPath(import.meta.resolve('mime')) }
          if (path === '@deepseek-ai/dsh-util-file-drag')
            return { path: join(root, 'packages/util/file-drag/src/index.ts') }
          if (existsIn(dependencyIndex)) return { path, external: true }
          if (!existsIn(runtimePackages))
            throw Error('Not shipped in the attested runtime: ' + path)
          const dir = 'dsh/node_modules/' + pkg.join('/')
          const manifest = JSON.parse(
            asar.extractFile(archive, dir + '/package.json'),
          )
          const key = names.length ? './' + names.join('/') : '.'
          let spec =
            manifest.exports?.[key] ?? (key === '.' ? manifest.main : undefined)
          while (spec && typeof spec === 'object')
            spec = spec.import ?? spec.node ?? spec.default
          if (!spec) throw Error('Missing release export: ' + path)
          const dest = join(dir, spec)
          asar.statFile(archive, dest)
          return { path: '../' + dest, external: true }
        })
      },
    },
  ],
})
replace('lib/main.js', output.outputFiles[0].contents)
for (const [local, pkg] of [
  ['base', 'dsh-base'],
  ['web-app', 'dsh-web-app'],
]) {
  const path = 'packages/bundle/' + local + '/cordis.patch.yml'
  const shipped = 'dsh/node_modules/@deepseek-ai/' + pkg + '/cordis.patch.yml'
  assert(
    asar
      .extractFile(archive, shipped)
      .equals(
        execFileSync('git', [
          '-C',
          upstream,
          'show',
          base + ':' + path,
        ]),
      ),
  )
  replace(shipped, readFileSync(join(root, path)))
}
info.productName = 'Local Harness'
delete info.dshMandatoryUpdatePolicy
replace('package.json', JSON.stringify(info))
const temp = mkdtempSync(join(tmpdir(), 'dsh-custom-build-'))
try {
  const newArchive = join(temp, 'app.asar')
  const streams = []
  for (const unixPath of asar.listPackage(archive, {})) {
    const path = unixPath.slice(1),
      node = asar.statFile(archive, path, false),
      unpacked = Boolean(node.unpacked)
    if (node.files) {
      streams.push({ path, type: 'directory', unpacked })
      continue
    }
    const local = archive + '.unpacked/' + path
    const data = () => {
      if (replacements.has(path)) return replacements.get(path)
      if (unpacked) return readFileSync(local)
      const start = 8 + raw.headerSize + Number(node.offset)
      return archiveBytes.subarray(start, start + node.size)
    }
    const common = {
      path,
      unpacked,
      stat: {
        size: replacements.get(path)?.length ?? node.size ?? 0,
        mode:
          unpacked && !node.link
            ? statSync(local).mode
            : node.executable
              ? 0o100755
              : 0o100644,
      },
      streamGenerator: () => Readable.from([data()]),
    }
    streams.push(
      node.link
        ? {
            ...common,
            type: 'link',
            symlink: relative(dirname(path), node.link),
          }
        : { ...common, type: 'file' },
    )
  }
  await asar.createPackageFromStreams(newArchive, streams)
  for (const [path, data] of replacements)
    assert(asar.extractFile(newArchive, path).equals(data))
  const out = join(temp, 'Local Harness.app')
  cmd('/usr/bin/ditto', [input, out])
  const res = join(out, 'Contents/Resources')
  renameSync(newArchive, join(res, 'app.asar'))
  cpSync(join(project, 'macos/host.sb'), join(res, 'local-host.sb'))
  rmSync(join(res, 'app-update.yml'), { force: true })
  const plist = join(out, 'Contents/Info.plist')
  const edit = (key, value) =>
    cmd('/usr/libexec/PlistBuddy', ['-c', 'Set :' + key + ' ' + value, plist])
  edit('CFBundleIdentifier', 'local.harness.offline.desktop')
  // Electron locates the shipped helper by CFBundleName; Finder uses CFBundleDisplayName.
  edit('CFBundleDisplayName', 'Local Harness')
  cmd('/usr/libexec/PlistBuddy', ['-c', 'Delete :CFBundleURLTypes', plist])
  edit(
    'ElectronAsarIntegrity:Resources/app.asar:hash',
    createHash('sha256')
      .update(asar.getRawHeader(join(res, 'app.asar')).headerString)
      .digest('hex'),
  )
  cmd('codesign', [
    '--force',
    '--sign',
    '-',
    '--preserve-metadata=entitlements',
    out,
  ])
  cmd('codesign', ['--verify', '--deep', '--strict', out])
  mkdirSync(dirname(resolve(target)), { recursive: true })
  renameSync(out, resolve(target))
  console.log('Built and verified', target)
} finally {
  rmSync(temp, { recursive: true, force: true })
}
