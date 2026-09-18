const fs = require('fs');
let content = fs.readFileSync('src/components/PopCard.tsx', 'utf8');

// 1. Remove the bulky Footer Table
const footerTableRegex = /\{\/\* Footer Table \*\/\}.*?<\/div>\s*<\/div>\s*<\/div>/s;
content = content.replace(footerTableRegex, '');

// 2. Add the slim ribbon below the 3 Bottom Boxes
const slimRibbon = `
      {/* 3 Bottom Boxes */}`;

// Wait, the footer table is AFTER the 3 bottom boxes, so I can just replace the footer table with the slim ribbon.
const newFooter = `      {/* Total Summary Ribbon */}
      <div className="mt-3.5 bg-slate-100 rounded-lg py-2 px-4 flex items-center justify-center gap-2 text-[11px] border border-slate-200">
        <span className="font-bold text-slate-700">{product.period}개월 총 체감가 :</span>
        <span className="font-black text-red-600 text-sm">{formatNumber(totalBenefitPrice)}원</span>
        <span className="text-slate-400 mx-1">|</span>
        <span className="font-bold text-slate-500">총 구독 원금 {formatNumber(calculatedDownPayment)}원</span>
      </div>
`;
content = content.replace(/\{\/\* Footer Table \*\/\}.*?<\/div>\s*<\/div>\s*<\/div>/s, newFooter);

// 3. Remove the inner gray bar from the Main Price Box to avoid duplication and clean it up
const innerGrayBarRegex = /\{\/\* 구독 계약금 및 최종 혜택가 \*\/\}.*?<\/div>/s;
content = content.replace(innerGrayBarRegex, '');

fs.writeFileSync('src/components/PopCard.tsx', content);
