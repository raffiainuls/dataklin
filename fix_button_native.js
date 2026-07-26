const fs = require('fs');

const file = process.argv[2];
if (!file) {
  console.error("Please provide a file path");
  process.exit(1);
}

let content = fs.readFileSync(file, 'utf8');

// Ensure nativeButton={false} is on all Button components that have a render prop
content = content.replace(/<Button([^>]*?)render={([^}]+)}([^>]*?)>/g, (match, before, renderContent, after) => {
  if (match.includes('nativeButton={false}')) return match;
  return `<Button${before}render={${renderContent}}${after} nativeButton={false}>`;
});

fs.writeFileSync(file, content);
console.log(`Fixed buttons in ${file}`);
