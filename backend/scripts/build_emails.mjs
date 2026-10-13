import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import mjml2html from 'mjml';

const source = new URL('../accounts/templates/accounts/emails/', import.meta.url);
const output = new URL('../.generated/templates/accounts/emails/', import.meta.url);
const templates = readdirSync(source).filter((name) => name.endsWith('.mjml')).sort();
const compiled = [];

for (const name of templates) {
  const file = new URL(name, source);
  const { html } = await mjml2html(readFileSync(file, 'utf8'), {
    filePath: fileURLToPath(file),
    ignoreIncludes: false,
    validationLevel: 'strict',
    fonts: {},
  });
  compiled.push([name.replace(/\.mjml$/, '.html'), html]);
}

mkdirSync(output, { recursive: true });
for (const [name, html] of compiled) writeFileSync(new URL(name, output), html);
const active = new Set(compiled.map(([name]) => name));
for (const name of readdirSync(output)) {
  if (name.endsWith('.html') && !active.has(name)) rmSync(new URL(name, output));
}
console.log(`Built ${compiled.length} MJML email templates.`);
