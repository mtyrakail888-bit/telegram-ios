# MyGram style: local emoji status, profile colors and custom profile background.
# Everything here is visible only on this device. Run from the Telegram-iOS source root.
import re

def read(p):
    return open(p, encoding="utf-8").read()

def write(p, s):
    open(p, "w", encoding="utf-8").write(s)

def insert_after_regex(s, pattern, text, what):
    matches = list(re.finditer(pattern, s))
    if len(matches) != 1:
        raise SystemExit("anchor not found (%d matches): %s" % (len(matches), what))
    i = matches[0].end()
    return s[:i] + text + s[i:]

# ---------------------------------------------------------------- 1) TelegramCore helpers
p = "submodules/TelegramCore/Sources/TelegramEngine/Peers/Peer.swift"
s = read(p)
if "func myGramVisualNotify" not in s:
    raise SystemExit("Step 'Visual profile' must run before this script")
s += r'''

// MARK: - MyGram style (local only)

private func myGramStyleEnabled() -> Bool {
    return UserDefaults.standard.bool(forKey: "MyGramFakePremium")
}

public func myGramApplyCosmetic(_ peer: EnginePeer?) -> EnginePeer? {
    guard let peer = peer, case let .user(user) = peer else {
        return peer
    }
    let d = UserDefaults.standard
    guard myGramStyleEnabled(), let selfId = (d.object(forKey: "MyGramSelfPeerId") as? NSNumber)?.int64Value, selfId == user.id.toInt64() else {
        return peer
    }
    var result = user
    if let statusId = (d.object(forKey: "MyGramEmojiStatusId") as? NSNumber)?.int64Value {
        result = result.withUpdatedEmojiStatus(PeerEmojiStatus(content: .emoji(fileId: statusId), expirationDate: nil))
    }
    if d.bool(forKey: "MyGramProfileStyleSet") {
        let color = (d.object(forKey: "MyGramProfileColor") as? NSNumber).map { PeerNameColor(rawValue: $0.int32Value) }
        result = result.withUpdatedProfileColor(color)
        result = result.withUpdatedProfileBackgroundEmojiId((d.object(forKey: "MyGramProfileBgEmoji") as? NSNumber)?.int64Value)
    }
    return .user(result)
}

public func myGramStoreLocalProfileStyle(profileColor: PeerNameColor?, profileBackgroundEmojiId: Int64?) {
    let d = UserDefaults.standard
    if let profileColor = profileColor {
        d.set(NSNumber(value: profileColor.rawValue), forKey: "MyGramProfileColor")
    } else {
        d.removeObject(forKey: "MyGramProfileColor")
    }
    if let emojiId = profileBackgroundEmojiId {
        d.set(NSNumber(value: emojiId), forKey: "MyGramProfileBgEmoji")
    } else {
        d.removeObject(forKey: "MyGramProfileBgEmoji")
    }
    d.set(true, forKey: "MyGramProfileStyleSet")
    DispatchQueue.main.async {
        myGramVisualNotify()
    }
}

public func myGramResetLocalStyle(emojiStatus: Bool, profileStyle: Bool) {
    let d = UserDefaults.standard
    if emojiStatus {
        d.removeObject(forKey: "MyGramEmojiStatusId")
    }
    if profileStyle {
        d.removeObject(forKey: "MyGramProfileColor")
        d.removeObject(forKey: "MyGramProfileBgEmoji")
        d.removeObject(forKey: "MyGramProfileStyleSet")
    }
    myGramVisualNotify()
}

public func myGramBackgroundDirectory() -> URL {
    let fm = FileManager.default
    let base = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
    var dir = base.appendingPathComponent("MyGramBackground", isDirectory: true)
    if !fm.fileExists(atPath: dir.path) {
        try? fm.createDirectory(at: dir, withIntermediateDirectories: true, attributes: nil)
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try? dir.setResourceValues(values)
        // move a background saved by the old version (Documents) if it still exists
        let oldDir = fm.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("MyGramBackground", isDirectory: true)
        if let items = try? fm.contentsOfDirectory(atPath: oldDir.path) {
            for item in items {
                try? fm.moveItem(atPath: oldDir.appendingPathComponent(item).path, toPath: dir.appendingPathComponent(item).path)
            }
        }
    }
    return dir
}

private func myGramNewestBackgroundName() -> String? {
    let dir = myGramBackgroundDirectory()
    guard let items = try? FileManager.default.contentsOfDirectory(atPath: dir.path) else {
        return nil
    }
    return items.filter { $0.hasPrefix("bg_") }.sorted().last
}

public func myGramCustomBackgroundPath() -> String? {
    let d = UserDefaults.standard
    if let name = d.string(forKey: "MyGramBgFile"), !name.isEmpty {
        let path = myGramBackgroundDirectory().appendingPathComponent(name).path
        if FileManager.default.fileExists(atPath: path) {
            return path
        }
    }
    if d.bool(forKey: "MyGramBgRemoved") {
        return nil
    }
    // the setting was lost but the file is still there: pick it up again
    guard let name = myGramNewestBackgroundName() else {
        return nil
    }
    d.set(name, forKey: "MyGramBgFile")
    return myGramBackgroundDirectory().appendingPathComponent(name).path
}

public func myGramCustomBackgroundStamp() -> Double {
    return UserDefaults.standard.double(forKey: "MyGramBgStamp")
}

public func myGramIsCustomBackgroundActive() -> Bool {
    guard myGramStyleEnabled(), let path = myGramCustomBackgroundPath() else {
        return false
    }
    return FileManager.default.fileExists(atPath: path)
}

public func myGramSetCustomBackground(data: Data?, ext: String) {
    let d = UserDefaults.standard
    let fm = FileManager.default
    let dir = myGramBackgroundDirectory()
    if let items = try? fm.contentsOfDirectory(atPath: dir.path) {
        for item in items {
            try? fm.removeItem(atPath: dir.appendingPathComponent(item).path)
        }
    }
    if let data = data {
        let name = "bg_\(Int64(Date().timeIntervalSince1970 * 1000.0)).\(ext)"
        let url = dir.appendingPathComponent(name)
        do {
            try data.write(to: url, options: .atomic)
            d.set(name, forKey: "MyGramBgFile")
            d.set(false, forKey: "MyGramBgRemoved")
        } catch {
            d.removeObject(forKey: "MyGramBgFile")
        }
    } else {
        d.removeObject(forKey: "MyGramBgFile")
        d.set(true, forKey: "MyGramBgRemoved")
    }
    d.set(Date().timeIntervalSince1970, forKey: "MyGramBgStamp")
    d.synchronize()
    DispatchQueue.main.async {
        myGramVisualNotify()
    }
}
'''
write(p, s)
print("patched Peer.swift")

# ---------------------------------------------------------------- 2) Engine: keep emoji status / profile style locally
p = "submodules/TelegramCore/Sources/TelegramEngine/AccountData/TelegramEngineAccountData.swift"
s = read(p)
s = insert_after_regex(s,
    r"public func setEmojiStatusWithResult\(file:\s*TelegramMediaFile\?,\s*expirationDate:\s*Int32\?\)\s*->\s*Signal<Never,\s*SetEmojiStatusError>\s*\{\n",
    "            if UserDefaults.standard.bool(forKey: \"MyGramFakePremium\") {\n"
    "                return myGramStoreLocalEmojiStatus(postbox: self.account.postbox, file: file)\n"
    "            }\n",
    "setEmojiStatusWithResult")
s = insert_after_regex(s,
    r"public func updateNameColorAndEmoji\(nameColor:\s*UpdateNameColor,\s*profileColor:\s*PeerNameColor\?,\s*profileBackgroundEmojiId:\s*Int64\?\)\s*->\s*Signal<Void,\s*UpdateNameColorAndEmojiError>\s*\{\n",
    "            if UserDefaults.standard.bool(forKey: \"MyGramFakePremium\") {\n"
    "                myGramStoreLocalProfileStyle(profileColor: profileColor, profileBackgroundEmojiId: profileBackgroundEmojiId)\n"
    "                return .single(Void())\n"
    "            }\n",
    "updateNameColorAndEmoji")
s += r'''

private func myGramStoreLocalEmojiStatus(postbox: Postbox, file: TelegramMediaFile?) -> Signal<Never, SetEmojiStatusError> {
    if let file = file {
        UserDefaults.standard.set(NSNumber(value: file.fileId.id), forKey: "MyGramEmojiStatusId")
    } else {
        UserDefaults.standard.removeObject(forKey: "MyGramEmojiStatusId")
    }
    return postbox.transaction { transaction -> Void in
        if let file = file {
            transaction.storeMediaIfNotPresent(media: file)
        }
    }
    |> castError(SetEmojiStatusError.self)
    |> ignoreValues
    |> afterCompleted {
        DispatchQueue.main.async {
            myGramVisualNotify()
        }
    }
}
'''
write(p, s)
print("patched TelegramEngineAccountData.swift")

# ---------------------------------------------------------------- 3) Profile data: apply local style
p = "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoData.swift"
s = read(p)
if "self.peer = myGramApplyVisual(peer)\n" in s:
    s = s.replace("self.peer = myGramApplyVisual(peer)\n", "self.peer = myGramApplyCosmetic(myGramApplyVisual(peer))\n", 1)
    s = s.replace("self.chatPeer = myGramApplyVisual(chatPeer)\n", "self.chatPeer = myGramApplyCosmetic(myGramApplyVisual(chatPeer))\n", 1)
else:
    raise SystemExit("PeerInfoData: visual anchors not found")
write(p, s)
print("patched PeerInfoData.swift")

# ---------------------------------------------------------------- 4) Appearance screen: allow "Apply style" in local premium
p = "submodules/TelegramUI/Components/Settings/PeerNameColorScreen/Sources/UserApperanceScreen.swift"
s = read(p)
old = "} else if !component.context.isPremium {"
if s.count(old) < 1:
    raise SystemExit("UserApperanceScreen: premium check not found")
s = s.replace(old, "} else if !component.context.isPremium && !UserDefaults.standard.bool(forKey: \"MyGramFakePremium\") {")
write(p, s)
print("patched UserApperanceScreen.swift")

# ---------------------------------------------------------------- 5) Profile header: photo / GIF / video background
p = "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoHeaderNode.swift"
s = read(p)
anchor = "self.backgroundBannerView.addSubview(backgroundCoverView)"
i = s.find(anchor)
if i < 0:
    raise SystemExit("PeerInfoHeaderNode: cover anchor not found")
j = s.find("if let profileGiftsContext, let peer {", i)
if j < 0:
    raise SystemExit("PeerInfoHeaderNode: gifts anchor not found")
line_start = s.rfind("\n", 0, j) + 1
indent = s[line_start:j]
call = indent + "myGramUpdateCustomBackground(container: self.backgroundBannerView, frame: CGRect(origin: CGPoint(x: 0.0, y: bannerFrame.height - backgroundCoverSize.height), size: CGSize(width: bannerFrame.width, height: backgroundCoverSize.height)), isSelf: peer?.id == self.context.account.peerId)\n"
s = s[:line_start] + call + s[line_start:]
s = "import AVFoundation\nimport ImageIO\n" + s
s += r'''

private final class MyGramBackgroundView: UIView {
    static let viewTag = 0x4D7947
    private let imageView = UIImageView()
    private var playerLayer: AVPlayerLayer?
    private var player: AVQueuePlayer?
    private var looper: AVPlayerLooper?
    private var loadedKey: String?

    override init(frame: CGRect) {
        super.init(frame: frame)
        self.tag = MyGramBackgroundView.viewTag
        self.clipsToBounds = true
        self.isUserInteractionEnabled = false
        self.imageView.contentMode = .scaleAspectFill
        self.imageView.clipsToBounds = true
        self.addSubview(self.imageView)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        self.imageView.frame = self.bounds
        self.playerLayer?.frame = self.bounds
    }

    override func willMove(toSuperview newSuperview: UIView?) {
        super.willMove(toSuperview: newSuperview)
        if newSuperview == nil {
            self.player?.pause()
        } else {
            self.player?.play()
        }
    }

    private func reset() {
        self.player?.pause()
        self.looper = nil
        self.player = nil
        self.playerLayer?.removeFromSuperlayer()
        self.playerLayer = nil
        self.imageView.stopAnimating()
        self.imageView.animationImages = nil
        self.imageView.image = nil
    }

    func load(path: String, stamp: Double) {
        let key = "\(path)#\(stamp)"
        if self.loadedKey == key {
            if let player = self.player, player.rate == 0.0 {
                player.play()
            }
            return
        }
        self.loadedKey = key
        self.reset()

        let url = URL(fileURLWithPath: path)
        let ext = url.pathExtension.lowercased()
        if ext == "mp4" || ext == "mov" || ext == "m4v" {
            let item = AVPlayerItem(url: url)
            let player = AVQueuePlayer()
            player.isMuted = true
            player.preventsDisplaySleepDuringVideoPlayback = false
            self.looper = AVPlayerLooper(player: player, templateItem: item)
            let layer = AVPlayerLayer(player: player)
            layer.videoGravity = .resizeAspectFill
            layer.frame = self.bounds
            self.layer.addSublayer(layer)
            self.player = player
            self.playerLayer = layer
            player.play()
        } else if ext == "gif", let data = try? Data(contentsOf: url), let source = CGImageSourceCreateWithData(data as CFData, nil) {
            var frames: [UIImage] = []
            var duration: Double = 0.0
            let count = min(CGImageSourceGetCount(source), 240)
            for index in 0 ..< count {
                guard let cgImage = CGImageSourceCreateImageAtIndex(source, index, nil) else {
                    continue
                }
                frames.append(UIImage(cgImage: cgImage))
                var delay = 0.1
                if let properties = CGImageSourceCopyPropertiesAtIndex(source, index, nil) as? [CFString: Any], let gif = properties[kCGImagePropertyGIFDictionary] as? [CFString: Any] {
                    if let value = gif[kCGImagePropertyGIFUnclampedDelayTime] as? Double, value > 0.01 {
                        delay = value
                    } else if let value = gif[kCGImagePropertyGIFDelayTime] as? Double, value > 0.01 {
                        delay = value
                    }
                }
                duration += delay
            }
            if frames.count > 1 {
                self.imageView.animationImages = frames
                self.imageView.animationDuration = duration
                self.imageView.startAnimating()
            } else {
                self.imageView.image = frames.first
            }
        } else {
            self.imageView.image = UIImage(contentsOfFile: path)
        }
    }
}

private func myGramUpdateCustomBackground(container: UIView, frame: CGRect, isSelf: Bool) {
    let existing = container.subviews.first(where: { $0.tag == MyGramBackgroundView.viewTag }) as? MyGramBackgroundView
    guard isSelf, myGramIsCustomBackgroundActive(), let path = myGramCustomBackgroundPath() else {
        existing?.removeFromSuperview()
        return
    }
    let view: MyGramBackgroundView
    if let existing = existing {
        view = existing
    } else {
        view = MyGramBackgroundView(frame: frame)
        container.addSubview(view)
    }
    container.bringSubviewToFront(view)
    view.frame = frame
    view.load(path: path, stamp: myGramCustomBackgroundStamp())
}
'''
write(p, s)
print("patched PeerInfoHeaderNode.swift")

# ---------------------------------------------------------------- 6) MyGram settings: style section
p = "submodules/SettingsUI/Sources/MyGramSettingsController.swift"
s = read(p)
s = insert_after_regex(s, r"\n[ \t]*case info\n", "    case action\n", "MyGramEntryKind.info")
s = insert_after_regex(s,
    r"case \.info:\n[ \t]*return ItemListTextItem\(presentationData: presentationData, text: \.plain\(self\.title\), sectionId: self\.section\)\n",
    "        case .action:\n"
    "            return ItemListActionItem(presentationData: presentationData, systemStyle: .glass, title: self.title, kind: .generic, alignment: .natural, sectionId: self.section, style: .blocks, action: {\n"
    "                myGramSettingsAction(key)\n"
    "            })\n",
    "item() .info case")
m = list(re.finditer(r"\n([ \t]*)return entries\n\}", s))
if len(m) != 1:
    raise SystemExit("settings: 'return entries' not found")
k = m[0].start() + 1
s = s[:k] + r'''    func action(_ section: Int32, _ id: Int32, _ title: String, _ key: String) {
        entries.append(MyGramEntry(kind: .action, sectionValue: section, id: id, title: title, key: key, text: "", flag: false, isNumber: false))
    }

    header(3, 30, "ОФОРМЛЕНИЕ (ВИДНО ТОЛЬКО ТЕБЕ)")
    action(3, 31, "Фон профиля: фото, GIF или видео", "pickBackground")
    if myGramCustomBackgroundPath() != nil {
        action(3, 32, "Убрать фон профиля", "removeBackground")
    }
    if d.object(forKey: "MyGramEmojiStatusId") != nil {
        action(3, 33, "Убрать эмодзи у ника", "removeEmojiStatus")
    }
    if d.bool(forKey: "MyGramProfileStyleSet") {
        action(3, 34, "Сбросить цвет профиля", "resetProfileStyle")
    }
    info(3, 35, "Работает, когда включён «Значок Premium». Эмодзи у ника: открой свой профиль и нажми на место рядом с именем или «Изменить статус». Цвет и фоновый эмодзи: Мой профиль → Изменить → Оформление → «Применить стиль». Всё это видишь только ты.")
''' + s[k:]
s += r'''

private final class MyGramMediaPicker: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
    static let shared = MyGramMediaPicker()

    func present() {
        guard UIImagePickerController.isSourceTypeAvailable(.photoLibrary) else {
            return
        }
        let picker = UIImagePickerController()
        picker.sourceType = .photoLibrary
        picker.mediaTypes = ["public.image", "public.movie"]
        picker.videoMaximumDuration = 60.0
        picker.videoQuality = .typeHigh
        picker.allowsEditing = false
        picker.delegate = self
        myGramTopViewController()?.present(picker, animated: true, completion: nil)
    }

    func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
        picker.dismiss(animated: true, completion: nil)
    }

    func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
        picker.dismiss(animated: true, completion: nil)
        DispatchQueue.global(qos: .userInitiated).async {
            if let url = info[.mediaURL] as? URL, let data = try? Data(contentsOf: url) {
                let ext = url.pathExtension.lowercased()
                myGramSetCustomBackground(data: data, ext: ext.isEmpty ? "mov" : ext)
            } else if let url = info[.imageURL] as? URL, url.pathExtension.lowercased() == "gif", let data = try? Data(contentsOf: url) {
                myGramSetCustomBackground(data: data, ext: "gif")
            } else if let image = info[.originalImage] as? UIImage, let data = image.jpegData(compressionQuality: 0.9) {
                myGramSetCustomBackground(data: data, ext: "jpg")
            }
        }
    }
}

private func myGramTopViewController() -> UIViewController? {
    let windows = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.flatMap { $0.windows }
    var controller = (windows.first(where: { $0.isKeyWindow }) ?? windows.first)?.rootViewController
    while let presented = controller?.presentedViewController {
        controller = presented
    }
    return controller
}

private func myGramSettingsAction(_ key: String) {
    switch key {
    case "pickBackground":
        MyGramMediaPicker.shared.present()
    case "removeBackground":
        myGramSetCustomBackground(data: nil, ext: "")
    case "removeEmojiStatus":
        myGramResetLocalStyle(emojiStatus: true, profileStyle: false)
    case "resetProfileStyle":
        myGramResetLocalStyle(emojiStatus: false, profileStyle: true)
    default:
        break
    }
}
'''
write(p, s)
print("patched MyGramSettingsController.swift")
print("MyGram style: done")
