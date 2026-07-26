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
  if (content.includes('onValueChange={set')) {
    content = content.replace(/onValueChange={set([A-Za-z0-9_]+)}/g, 'onValueChange={(val) => set$1(val || "")}');
    fs.writeFileSync(file, content);
    console.log(`Fixed Select in ${file}`);
  }
}
