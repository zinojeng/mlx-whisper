import SwiftUI

struct ContentView: View {
    @StateObject private var vm = VoiceInputViewModel()
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()

                // 狀態文字
                Text(vm.statusText)
                    .font(.headline)
                    .foregroundStyle(vm.isRecording ? .red : .secondary)

                // Push-to-talk 按鈕
                RecordButton(isRecording: vm.isRecording, isProcessing: vm.isProcessing) {
                    vm.startRecording()
                } onRelease: {
                    vm.stopAndProcess()
                }

                // 結果顯示
                if !vm.resultText.isEmpty {
                    ResultCard(text: vm.resultText, onCopy: vm.copyToClipboard)
                }

                Spacer()

                // LLM / Context / Style 狀態列
                HStack(spacing: 12) {
                    Label(vm.llmEnabled ? "LLM ON" : "LLM OFF",
                          systemImage: vm.llmEnabled ? "brain.fill" : "brain")
                        .font(.caption)
                        .foregroundStyle(vm.llmEnabled ? .green : .secondary)

                    if !vm.context.isEmpty {
                        Label(vm.context, systemImage: "text.magnifyingglass")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Label(vm.style.capitalized, systemImage: "textformat")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 8)
            }
            .padding()
            .navigationTitle("語音輸入")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape")
                    }
                }
            }
            .sheet(isPresented: $showSettings) {
                SettingsView(vm: vm)
            }
            .alert("錯誤", isPresented: $vm.showError) {
                Button("確定", role: .cancel) {}
            } message: {
                Text(vm.errorMessage)
            }
        }
    }
}

// MARK: - 錄音按鈕（按住錄音，放開停止）

struct RecordButton: View {
    let isRecording: Bool
    let isProcessing: Bool
    let onPress: () -> Void
    let onRelease: () -> Void

    var body: some View {
        Circle()
            .fill(isRecording ? Color.red : (isProcessing ? Color.orange : Color.accentColor))
            .frame(width: 120, height: 120)
            .overlay {
                if isProcessing {
                    ProgressView()
                        .tint(.white)
                        .scaleEffect(1.5)
                } else {
                    Image(systemName: isRecording ? "waveform" : "mic.fill")
                        .font(.system(size: 40))
                        .foregroundStyle(.white)
                        .symbolEffect(.variableColor.iterative, isActive: isRecording)
                }
            }
            .shadow(color: isRecording ? .red.opacity(0.4) : .clear, radius: 20)
            .gesture(
                LongPressGesture(minimumDuration: 0.2)
                    .sequenced(before: DragGesture(minimumDistance: 0))
                    .onChanged { value in
                        switch value {
                        case .second(true, _):
                            if !isRecording && !isProcessing {
                                onPress()
                            }
                        default:
                            break
                        }
                    }
                    .onEnded { _ in
                        if isRecording {
                            onRelease()
                        }
                    }
            )
            .animation(.easeInOut(duration: 0.2), value: isRecording)
            .animation(.easeInOut(duration: 0.2), value: isProcessing)
    }
}

// MARK: - 結果卡片

struct ResultCard: View {
    let text: String
    let onCopy: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(text)
                .font(.body)
                .textSelection(.enabled)

            HStack {
                Spacer()
                Button {
                    onCopy()
                } label: {
                    Label("複製", systemImage: "doc.on.doc")
                        .font(.caption)
                }
                .buttonStyle(.bordered)
            }
        }
        .padding()
        .background(.ultraThinMaterial)
        .cornerRadius(12)
    }
}

#Preview {
    ContentView()
}
