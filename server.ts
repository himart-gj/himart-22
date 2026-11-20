import "dotenv/config";
import express from "express";
import path from "path";
import { parseQuoteImageWithGemini } from "./src/lib/parseImageWithGemini.ts";

async function startServer() {
  const app = express();
  const PORT = 3000;

  // 대용량 이미지(사진) base64 처리를 위해 50mb로 확장
  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ limit: "50mb", extended: true }));

  // AI 견적서/POS 사진 자동 분석 엔드포인트
  app.post("/api/ai/parse-image", async (req, res) => {
    try {
      const { image, mimeType = "image/jpeg", apiKey: clientApiKey, model: clientModel } = req.body;
      if (!image) {
        return res.status(400).json({ success: false, error: "이미지 데이터가 전달되지 않았습니다." });
      }

      const apiKey = clientApiKey || process.env.GEMINI_API_KEY;
      if (!apiKey) {
        return res.status(400).json({ success: false, error: "Gemini API 키가 설정되지 않았습니다." });
      }

      const parsedData = await parseQuoteImageWithGemini({
        image,
        mimeType,
        apiKey,
        preferredModel: clientModel,
        httpOptions: {
          headers: {
            "User-Agent": "aistudio-build",
          },
        },
      });

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
    const { createServer: createViteServer } = await import("vite");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on port ${PORT}`);
  });
}

startServer();
