import SwiftUI

struct SettingsView: View {
    @ObservedObject var vm: VoiceInputViewModel
    @Environment(\.dismiss) private var dismiss

    private let contextOptions = ["", "醫學研究", "軟體開發", "財務報告"]
    private let styleOptions = ["professional", "concise", "bullet", "casual"]
    private let styleLabels = [
        "professional": "Professional — 專業書面語",
        "concise": "Concise — 極度精簡",
        "bullet": "Bullet — 條列式",
        "casual": "Casual — 口語親切",
    ]
    private let languageOptions = ["zh-TW", "zh-CN", "en-US", "ja-JP"]
    private let languageLabels = [
        "zh-TW": "繁體中文（台灣）",
        "zh-CN": "簡體中文",
        "en-US": "English (US)",
        "ja-JP": "日本語",
    ]

    var body: some View {
        NavigationStack {
            Form {
                // MARK: - API Key
                Section {
                    SecureField("xAI API Key", text: $vm.apiKey)
                        .textContentType(.password)
                        .autocorrectionDisabled()
                } header: {
                    Text("Grok API")
                } footer: {
                    Text("輸入 xAI API Key 以啟用 LLM 後處理。取得 Key：x.ai")
                }

                // MARK: - LLM 設定
                Section("LLM 後處理") {
                    Toggle("啟用 LLM 修飾", isOn: $vm.llmEnabled)

                    Picker("領域上下文", selection: $vm.context) {
                        Text("無").tag("")
                        ForEach(contextOptions.filter { !$0.isEmpty }, id: \.self) { ctx in
                            Text(ctx).tag(ctx)
                        }
                    }

                    Picker("輸出風格", selection: $vm.style) {
                        ForEach(styleOptions, id: \.self) { s in
                            Text(styleLabels[s] ?? s).tag(s)
                        }
                    }
                }

                // MARK: - 語音辨識
                Section("語音辨識") {
                    Picker("語言", selection: $vm.language) {
                        ForEach(languageOptions, id: \.self) { lang in
                            Text(languageLabels[lang] ?? lang).tag(lang)
                        }
                    }
                }

                // MARK: - 關於
                Section("關於") {
                    LabeledContent("版本", value: "1.0.0")
                    LabeledContent("ASR 引擎", value: "Apple Speech")
                    LabeledContent("LLM", value: "Grok (xAI)")
                }
            }
            .navigationTitle("設定")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") { dismiss() }
                }
            }
        }
    }
}

#Preview {
    SettingsView(vm: VoiceInputViewModel())
}
