const fs = require('fs');
const path = require('path');

function replaceRenderNative(content) {
  // If a Button has render={<Link.../>} or render={<a.../>}, it should have nativeButton={false}
  return content.replace(/<Button([^>]*)render=\{<(Link|a)([^>]*)>\}([^>]*)>/g, 
    (match, preAttr, tag, linkAttr, postAttr) => {
      if (match.includes('nativeButton={false}')) return match;
      return `<Button${preAttr}render={<${tag}${linkAttr}>}${postAttr} nativeButton={false}>`;
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
      
      if (content.includes('render={<') && content.includes('<Button')) {
        const newContent = replaceRenderNative(content);
        if (content !== newContent) {
          fs.writeFileSync(fullPath, newContent);
          console.log(`Updated: ${fullPath}`);
        }
      }
    }
  }
}

processDirectory('./app');
