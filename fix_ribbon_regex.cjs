const fs = require('fs');
let content = fs.readFileSync('src/components/PopCard.tsx', 'utf8');

const boxesEndRegex = /<\/div>\s*<\/div>\s*<p className="text-\[8px\] text-slate-400 text-center mt-2 font-medium">/;

const ribbonStr = `      </div>

      {/* Total Summary Ribbon */}
      <div className="mt-3 bg-slate-100 rounded-lg py-1.5 px-4 flex items-center justify-center gap-1.5 text-[11px] border border-slate-200">
        <span className="font-bold text-slate-700">{product.period}개월 총 체감가:</span>
        <span className="font-black text-red-600 text-[13px]">{formatNumber(totalBenefitPrice)}원</span>
        <span className="text-slate-500 font-bold ml-1">(원금 {formatNumber(calculatedDownPayment)}원)</span>
      </div>
      
      <p className="text-[8px] text-slate-400 text-center mt-2 font-medium">`;

content = content.replace(boxesEndRegex, ribbonStr);

fs.writeFileSync('src/components/PopCard.tsx', content);
