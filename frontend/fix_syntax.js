const fs = require('fs');

function fixSyntax(file) {
  let content = fs.readFileSync(file, 'utf8');
  content = content.replace(/render={<Link href={([^}]+)} \/ nativeButton={false}>} nativeButton={false}>/g, 'render={<Link href={$1} />} nativeButton={false}>');
  content = content.replace(/render={<Link href={`([^`]+)`} \/ nativeButton={false}>} nativeButton={false}>/g, 'render={<Link href={`$1`} />} nativeButton={false}>');
  
  // also catch cases where it might be slightly different
  content = content.replace(/render={<Link href={([^}]+)} \/ nativeButton={false}>}/g, 'render={<Link href={$1} />}');
  content = content.replace(/render={<Link href={`([^`]+)`} \/ nativeButton={false}>}/g, 'render={<Link href={`$1`} />}');
  content = content.replace(/render={<Link href=([^ >]+) \/ nativeButton={false}>}/g, 'render={<Link href=$1 />}');
  
  fs.writeFileSync(file, content);
  console.log(`Fixed syntax in ${file}`);
}

fixSyntax('app/review/page.tsx');
fixSyntax('app/runs/page.tsx');
