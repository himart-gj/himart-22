const fs = require('fs');
let content = fs.readFileSync('src/components/PopCard.tsx', 'utf8');

// Reduce border size slightly for print
content = content.replace(/print:border-\[8px\]/g, 'print:border-[6px]');
// Make padding slightly smaller in print so it doesn't overflow since we reduced width
content = content.replace(/px-6 pt-6 pb-10/g, 'px-6 pt-6 pb-10 print:px-5 print:pt-5 print:pb-8');

fs.writeFileSync('src/components/PopCard.tsx', content);
