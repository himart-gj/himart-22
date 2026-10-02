import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type } from "@google/genai";

async function startServer() {
  const app = express();
  const PORT = 3000;

  // 대용량 이미지(사진) base64 처리를 위해 50mb로 확장
  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ limit: "50mb", extended: true }));

  // AI 견적서/POS 사진 자동 분석 엔드포인트
  app.post("/api/ai/parse-image", async (req, res) => {
    try {
      const { image, mimeType = "image/jpeg", apiKey: clientApiKey } = req.body;
      if (!image) {
        return res.status(400).json({ success: false, error: "이미지 데이터가 전달되지 않았습니다." });
      }

      const apiKey = clientApiKey || process.env.GEMINI_API_KEY;
      if (!apiKey) {
        return res.status(400).json({ success: false, error: "Gemini API 키가 설정되지 않았습니다." });
      }

      // data:image/...;base64, 접두사 제거
      const cleanBase64 = image.includes("base64,")
        ? image.split("base64,")[1]
        : image;

      const ai = new GoogleGenAI({
        apiKey,
        httpOptions: {
          headers: {
            "User-Agent": "aistudio-build",
          },
        },
      });

      const prompt = `당신은 가전제품 구독/렌탈 견적서 및 POS 화면 이미지 분석 전문가입니다.
사용자가 업로드한 화면 캡처 또는 사진에서 다음 구독 POP 제작에 필요한 핵심 정보들을 정확하게 추출하세요.

[필드 추출 가이드]
1. category (품목): 가전제품 품목명 (예: 전기밥솥, 냉장고, 김치냉장고, 세탁기, 건조기, 에어컨, 정수기, TV, 청소기, 공기청정기 등). 상품명에서 품목을 알 수 있다면 정확한 품목명만 간결하게 추출 (예: '쿠쿠전자 트윈프레셔압력 전기밥솥'이면 '전기밥솥').
2. modelName (제품 모델명): 정확한 모델명/모델코드 (예: CRP-PHFFTR0620FGW, WF24B9600KP 등).
3. productName (상품 전체 이름): 상품명 풀네임 (예: 쿠쿠전자 트윈프레셔압력 전기밥솥).
4. monthlyFee (월 구독료): 정기 월 구독료/월 납부요금 (숫자 정수). 제휴카드 할인 전 기본 월 구독료 또는 화면에 '월 납부요금', '월 구독료', '월 렌탈료'로 적힌 대표 금액 (예: 약 18,094원이면 18094).
5. period (구독기간): 구독 개월 수 정수 숫자 (예: 36, 48, 60 등).
6. downPayment (계약금/선납금): 초기 납부금/계약금 (숫자, 없거나 0원이면 0).
7. careServiceText (케어서비스): 케어 패키지 또는 서비스 명칭 (예: 안심케어_1, 셀프케어 등).
8. careServiceCycle (방문/배송주기): 케어 주기 (예: 12/24개월, 3개월 등).
9. careServiceCount (제공횟수): 케어 제공 횟수 (예: 2회 등).
10. careServiceDetail (보증/서비스상세): 보장 서비스 및 세부 내용 (예: AS연장보험, 고무패킹 정기배송 등).
11. isAllCare (올케어 여부): 이미지에 '올케어', 'allcare', '사용중 가전 보증', '2년 수리비 보증' 등이 포함되어 있으면 true, 아니면 false.`;

      let responseText = "";
      const modelsToTry = ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3.8-flash"];
      let lastError: any = null;

      for (const model of modelsToTry) {
        try {
          const response = await ai.models.generateContent({
            model,
            contents: [
              {
                role: "user",
                parts: [
                  {
                    inlineData: {
                      mimeType: mimeType || "image/jpeg",
                      data: cleanBase64,
                    },
                  },
                  {
                    text: prompt,
                  },
                ],
              },
            ],
            config: {
              responseMimeType: "application/json",
              responseSchema: {
                type: Type.OBJECT,
                properties: {
                  category: { type: Type.STRING, description: "품목명 (예: 전기밥솥, 냉장고)" },
                  modelName: { type: Type.STRING, description: "제품 모델명 코드" },
                  productName: { type: Type.STRING, description: "상품 풀네임" },
                  monthlyFee: { type: Type.INTEGER, description: "월 구독료 (숫자)" },
                  period: { type: Type.INTEGER, description: "구독 개월수 (숫자)" },
                  downPayment: { type: Type.INTEGER, description: "계약금/초기비용 (숫자, 없으면 0)" },
                  careServiceText: { type: Type.STRING, description: "케어서비스 명칭" },
                  careServiceCycle: { type: Type.STRING, description: "케어 주기" },
                  careServiceCount: { type: Type.STRING, description: "케어 횟수" },
                  careServiceDetail: { type: Type.STRING, description: "보증 및 케어 상세" },
                  isAllCare: { type: Type.BOOLEAN, description: "올케어 여부" },
                },
                required: ["category", "modelName", "monthlyFee", "period"],
              },
            },
          });

          if (response && response.text) {
            responseText = response.text.trim();
            break;
          }
        } catch (err: any) {
          console.warn(`[AI Parse] Model ${model} failed, trying next...`, err.message);
          lastError = err;
        }
      }

      if (!responseText) {
        throw lastError || new Error("AI 분석 응답을 받지 못했습니다.");
      }

      const parsedData = JSON.parse(responseText);
      return res.json({
        success: true,
        data: parsedData,
      });
    } catch (error: any) {
      console.error("[AI Image Parse Error]", error);
      return res.status(500).json({
        success: false,
        error: error.message || "이미지 분석 중 오류가 발생했습니다.",
      });
    }
  });

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on port ${PORT}`);
  });
}

startServer();
