import AVFoundation
import Speech
import SwiftUI

@MainActor
final class VoiceInputViewModel: ObservableObject {
    // MARK: - Published state

    @Published var isRecording = false
    @Published var isProcessing = false
    @Published var statusText = "按住按鈕開始錄音"
    @Published var resultText = ""
    @Published var showError = false
    @Published var errorMessage = ""

    // Settings
    @Published var apiKey: String {
        didSet { UserDefaults.standard.set(apiKey, forKey: "xai_api_key") }
    }
    @Published var llmEnabled: Bool {
        didSet { UserDefaults.standard.set(llmEnabled, forKey: "llm_enabled") }
    }
    @Published var context: String {
        didSet { UserDefaults.standard.set(context, forKey: "llm_context") }
    }
    @Published var style: String {
        didSet { UserDefaults.standard.set(style, forKey: "llm_style") }
    }
    @Published var language: String {
        didSet { UserDefaults.standard.set(language, forKey: "speech_language") }
    }

    // MARK: - Private

    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var speechRecognizer: SFSpeechRecognizer?

    // MARK: - Init

    init() {
        self.apiKey = UserDefaults.standard.string(forKey: "xai_api_key") ?? ""
        self.llmEnabled = UserDefaults.standard.object(forKey: "llm_enabled") as? Bool ?? true
        self.context = UserDefaults.standard.string(forKey: "llm_context") ?? ""
        self.style = UserDefaults.standard.string(forKey: "llm_style") ?? "professional"
        self.language = UserDefaults.standard.string(forKey: "speech_language") ?? "zh-TW"

        self.speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: language))
    }

    // MARK: - Permissions

    func requestPermissions() async -> Bool {
        let speechStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }
        guard speechStatus == .authorized else {
            showErrorAlert("請在「設定」中允許語音辨識權限")
            return false
        }

        let micStatus = await AVAudioApplication.requestRecordPermission()
        guard micStatus else {
            showErrorAlert("請在「設定」中允許麥克風權限")
            return false
        }
        return true
    }

    // MARK: - Recording

    func startRecording() {
        Task {
            guard await requestPermissions() else { return }

            // 更新語言設定
            speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: language))
            guard let speechRecognizer, speechRecognizer.isAvailable else {
                showErrorAlert("語音辨識不可用（語言：\(language)）")
                return
            }

            do {
                let audioSession = AVAudioSession.sharedInstance()
                try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
                try audioSession.setActive(true, options: .notifyOthersOnDeactivation)

                recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
                guard let recognitionRequest else { return }
                recognitionRequest.shouldReportPartialResults = true
                recognitionRequest.requiresOnDeviceRecognition = speechRecognizer.supportsOnDeviceRecognition

                let inputNode = audioEngine.inputNode
                let recordingFormat = inputNode.outputFormat(forBus: 0)
                inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
                    recognitionRequest.append(buffer)
                }

                audioEngine.prepare()
                try audioEngine.start()

                isRecording = true
                statusText = "錄音中..."

                recognitionTask = speechRecognizer.recognitionTask(with: recognitionRequest) { [weak self] result, error in
                    Task { @MainActor in
                        if let result {
                            self?.resultText = result.bestTranscription.formattedString
                        }
                        if error != nil {
                            self?.stopAudioEngine()
                        }
                    }
                }
            } catch {
                showErrorAlert("無法啟動錄音：\(error.localizedDescription)")
                stopAudioEngine()
            }
        }
    }

    func stopAndProcess() {
        guard isRecording else { return }

        stopAudioEngine()
        let rawText = resultText

        guard !rawText.isEmpty else {
            statusText = "未偵測到語音"
            return
        }

        // LLM 後處理
        if llmEnabled && !apiKey.isEmpty {
            isProcessing = true
            statusText = "LLM 處理中..."
            Task {
                let refined = await GrokService.refine(
                    text: rawText,
                    apiKey: apiKey,
                    context: context,
                    style: style
                )
                isProcessing = false
                resultText = refined ?? rawText
                statusText = "完成！"
                copyToClipboard()
            }
        } else {
            statusText = "完成！"
            copyToClipboard()
        }
    }

    func copyToClipboard() {
        UIPasteboard.general.string = resultText
        statusText = "已複製到剪貼簿 ✓"
    }

    // MARK: - Private

    private func stopAudioEngine() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionRequest = nil
        recognitionTask?.cancel()
        recognitionTask = nil
        isRecording = false
    }

    private func showErrorAlert(_ msg: String) {
        errorMessage = msg
        showError = true
    }
}
