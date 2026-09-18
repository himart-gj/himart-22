const fs = require('fs');
let content = fs.readFileSync('src/components/PopCard.tsx', 'utf8');

// I might have an extra </div> or a missing JSX wrapper somewhere.
// Let's run a small regex check
