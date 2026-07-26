const fs = require('fs');
const path = require('path');

function findFiles(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    file = path.join(dir, file);
    const stat = fs.statSync(file);
    if (stat && stat.isDirectory()) {
      results = results.concat(findFiles(file));
    } else if (file.endsWith('.tsx')) {
      results.push(file);
    }
  });
  return results;
}

const files = findFiles('app');
for (const file of files) {
  let content = fs.readFileSync(file, 'utf8');
  if (content.match(/onValueChange={\(val\) => set([A-Za-z0-9_]+)\(\{\.\.\.[A-Za-z0-9_]+, ([A-Za-z0-9_]+): val\}\)}/)) {
    content = content.replace(/onValueChange={\(val\) => set([A-Za-z0-9_]+)\(\{\.\.\.([A-Za-z0-9_]+), ([A-Za-z0-9_]+): val\}\)}/g, 'onValueChange={(val) => set$1({...$2, $3: val || ""})}');
    fs.writeFileSync(file, content);
    console.log(`Fixed form Select in ${file}`);
  }
}
