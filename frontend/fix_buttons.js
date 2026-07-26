const fs = require('fs');
const path = require('path');

function replaceAsChild(content) {
  // Regex untuk mencocokkan <Button ... asChild ...>
  return content.replace(/<Button([^>]*)asChild([^>]*)>\s*<Link([^>]*)>(.*?)<\/Link>\s*<\/Button>/gs, 
    (match, preAttr, postAttr, linkAttr, innerContent) => {
      // Mengonversi asChild menjadi pola render prop @base-ui/react
      return `<Button${preAttr}${postAttr}render={<Link${linkAttr} />}>\n  ${innerContent.trim()}\n</Button>`;
    }
  ).replace(/<Button([^>]*)asChild([^>]*)>\s*<a([^>]*)>(.*?)<\/a>\s*<\/Button>/gs,
    (match, preAttr, postAttr, linkAttr, innerContent) => {
      return `<Button${preAttr}${postAttr}render={<a${linkAttr} />}>\n  ${innerContent.trim()}\n</Button>`;
    }
  );
}

function processDirectory(dir) {
  const files = fs.readdirSync(dir);
  
  for (const file of files) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      processDirectory(fullPath);
    } else if (fullPath.endsWith('.tsx') || fullPath.endsWith('.jsx')) {
      let content = fs.readFileSync(fullPath, 'utf8');
      
      if (content.includes('asChild') && content.includes('<Button')) {
        const newContent = replaceAsChild(content);
        if (content !== newContent) {
          fs.writeFileSync(fullPath, newContent);
          console.log(`Updated: ${fullPath}`);
        }
      }
    }
  }
}

processDirectory('./app');
