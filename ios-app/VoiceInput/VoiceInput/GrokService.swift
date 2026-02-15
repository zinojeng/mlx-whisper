import Foundation

/// xAI Grok API 客戶端 — 與 macOS 版 llm_refine.py 對齊
enum GrokService {
    private static let baseURL = "https://api.x.ai/v1/chat/completions"
    private static let model = "grok-4-1-fast-reasoning"
    private static let timeout: TimeInterval = 30

    /// 呼叫 Grok API 修飾語音辨識文字
    static func refine(
        text: String,
        apiKey: String,
        context: String = "",
        style: String = "professional"
    ) async -> String? {
        guard !apiKey.isEmpty else { return nil }

        let systemPrompt = buildPrompt(context: context, style: style)

        let body: [String: Any] = [
            "model": model,
            "messages": [
                ["role": "system", "content": systemPrompt],
                ["role": "user", "content": text]
            ],
            "temperature": 0.3
        ]

        guard let jsonData = try? JSONSerialization.data(withJSONObject: body),
              let url = URL(string: baseURL) else { return nil }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.httpBody = jsonData
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.timeoutInterval = timeout

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else { return nil }

            guard httpResponse.statusCode == 200 else {
                let statusCode = httpResponse.statusCode
                let body = String(data: data, encoding: .utf8) ?? "(unreadable)"
                switch statusCode {
                case 401:
                    print("[GrokService] 401 Unauthorized — API key 無效或過期")
                case 429:
                    print("[GrokService] 429 Rate Limited — 請求頻率過高")
                case 500...599:
                    print("[GrokService] \(statusCode) Server Error — \(body)")
                default:
                    print("[GrokService] HTTP \(statusCode) — \(body)")
                }
                return nil
            }

            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let choices = json["choices"] as? [[String: Any]],
               let message = choices.first?["message"] as? [String: Any],
               let content = message["content"] as? String {
                return content.trimmingCharacters(in: .whitespacesAndNewlines)
            }
        } catch {
            print("[GrokService] Network error: \(error.localizedDescription)")
        }
        return nil
    }

    // MARK: - Prompt 組裝（與 llm_refine.py 一致）

    private static func buildPrompt(context: String, style: String) -> String {
        var prompt = """
        你是專業的語音辨識後處理助手。你的任務是將語音辨識的原始輸出修正為高品質的書面文字。

        處理規則：
        1. 修正明顯的同音錯字（根據上下文語意推論正確用字）
        2. 加入適當的標點符號（逗號、句號、問號、驚嘆號）
        3. 移除口頭禪和填充詞（嗯、啊、就是、然後、那個、對、所以、基本上）
        4. 移除不自然的重複
        5. 適當分段（長段落在語意轉換處換行）
        6. 保留原始語意，不要增添或刪減內容
        7. 口語數字轉為阿拉伯數字（三百五十 → 350）
        8. 專業術語加註英文（如適用）
        9. 中英夾雜時保持自然的 code-switching
        10. 使用台灣繁體中文用語
        """

        if !context.isEmpty {
            let safeContext = String(context.prefix(50))
                .replacingOccurrences(of: "\n", with: " ")
                .replacingOccurrences(of: "#", with: "")
            prompt += "\n\n領域上下文：\(safeContext)\n請根據此領域推論專業術語和同音錯字。"
        }

        let styleInstruction: String
        switch style {
        case "concise":
            styleInstruction = "極度精簡，只留核心資訊。"
        case "bullet":
            styleInstruction = "以條列式要點呈現，每點以「- 」開頭。"
        case "casual":
            styleInstruction = "口語親切風格，保持自然。"
        default: // professional
            styleInstruction = "專業書面語，語氣正式。"
        }
        prompt += "\n\n輸出風格：\(styleInstruction)"

        prompt += "\n\n重要：只輸出修正後的文字，不要加任何說明、前綴或後綴。"

        return prompt
    }
}
