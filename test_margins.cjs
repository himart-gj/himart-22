const fs = require('fs');
let app = fs.readFileSync('src/App.tsx', 'utf8');

// remove scale-[0.95] and center the cards cleanly.
app = app.replace(/print:scale-\[0\.95\] origin-center/g, 'print:p-2');

fs.writeFileSync('src/App.tsx', app);
