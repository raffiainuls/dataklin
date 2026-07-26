const fs = require('fs');

const file = process.argv[2];
if (!file) {
  console.error("Please provide a file path");
  process.exit(1);
}

let content = fs.readFileSync(file, 'utf8');

// Fix button asChild -> render prop pattern
content = content.replace(/<Button\s+([^>]*?)asChild([^>]*?)>([\s\S]*?)<\/Button>/g, (match, before, after, children) => {
  // If it's a link, we need to extract the href and wrap it correctly
  const linkMatch = children.match(/<Link\s+href=({[^}]+}|"[^"]+")([^>]*)>/);
  if (linkMatch) {
    const linkAttributes = linkMatch[0];
    return `<Button ${before}${after} render={${linkAttributes} />} nativeButton={false}>${children.replace(linkAttributes, '').replace(/<\/Link>/, '')}</Button>`.replace(/\s+/g, ' ');
  }
  return match;
});

// Also fix buttons containing links but no asChild
content = content.replace(/<Button([^>]*?)>([\s\S]*?)<Link\s+href=({[^}]+}|"[^"]+")([^>]*)>([\s\S]*?)<\/Link>([\s\S]*?)<\/Button>/g, (match, attrs, beforeLink, href, otherLinkAttrs, linkText, afterLink) => {
  return `<Button${attrs} render={<Link href=${href}${otherLinkAttrs} />} nativeButton={false}>\n  ${beforeLink}${linkText}${afterLink}\n</Button>`;
});

fs.writeFileSync(file, content);
console.log(`Fixed buttons in ${file}`);
