const fs = require('fs');
let app = fs.readFileSync('src/App.tsx', 'utf8');

app = app.replace(/print:p-\[10mm\]/g, 'print:p-[6mm]');

fs.writeFileSync('src/App.tsx', app);
