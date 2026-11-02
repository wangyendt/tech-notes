---
type: article
title: iPhone 与 Apple Watch 不显示开发者模式时，如何开启
description: 通过 Xcode Device Hub 发起开发配对，让手机和手表显示开发者模式入口，并完成重启确认与状态检查。
tags: [iOS, watchOS, Xcode, 开发者模式, 设备配对]
date: 2026-11-02
updated: 2026-11-02
---

# iPhone 与 Apple Watch 不显示开发者模式时，如何开启

新手机、新手表，或刚重置的设备，可能在“设置”的“隐私与安全”中找不到“开发者模式”。先在 Mac 上用 Xcode 发起开发配对，再回到设备上找开关；不要只在设置里反复查找。

Apple 说明，设备开始与 Mac 配对后，开发者模式入口才可能出现。入口出现后，手机和手表都要分别开启、重启，并在重启后确认。**打开开关不是最后一步。** [Apple：开启开发者模式](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)

本文用于通过 Xcode 安装、调试开发签名的 App。仅从 App Store 或 TestFlight 安装 App，不需要做这些操作。开发者模式会开放开发和调试能力，只在自己的设备与可信 Mac 之间启用。

## 开始前

- 在 Mac 上安装支持设备系统版本的完整 Xcode，并完成首次启动所需组件的安装。
- 用支持数据传输的线缆连接 iPhone 与 Mac，解锁手机；出现“信任此电脑”时，确认这是自己的 Mac，再轻点“信任”。
- 让 Mac、iPhone 和 Apple Watch 接入同一 Wi-Fi，开启手机和手表的蓝牙，保持设备靠近并解锁。
- 如果手表仍停留在初始配对界面，先在 iPhone 的 Watch App 中添加手表，完成日常使用所需的配对。已经完成的，不必重做。

这里有两种配对，不能混为一谈：

| 配对关系 | 用途 | 操作入口 |
|---|---|---|
| Apple Watch 与 iPhone | 让手机管理和使用手表 | iPhone 上的 Watch App |
| iPhone、Apple Watch 与 Mac | 安装和调试开发 App | Xcode 的设备管理工具 |

下面的界面步骤以 Xcode 27.2 的 **Device Hub** 为准。本次手机为 iOS 27.2；手表重置后的系统版本未重新读取，不能用 Mac 缓存中的旧版本代替。旧版 Xcode 的设备管理入口可能是 **Window > Devices and Simulators**，不必照找 Device Hub 的同名按钮。

## 1. 在 Mac 上发起开发配对

1. 在 Xcode 中选择 **Xcode > Open Developer Tool > Device Hub**。
2. 在 Device Hub 的设备列表中选择连接的 iPhone。如果出现 **Pair**，点按它，并完成手机上的信任提示。
3. 如果手机仍没有“开发者模式”，在 Device Hub 中点按 **Add（+）> Pair Nearby Device…**。
4. 在配对窗口中选择 iPhone 与 Apple Watch 对应的设备类型。窗口显示 **Waiting to pair** 后，保持窗口打开。
5. 在 iPhone 上退出当前“设置”页面，再进入 **设置 > 隐私与安全**，检查是否出现“开发者模式”。

**预期结果：**手机上出现“开发者模式”入口。Device Hub 可能仍显示 **Enable Developer Mode**；这时应转到手机操作，不是继续在 Mac 上寻找一个代替手机确认的按钮。

本次处理在重新执行手机配对、打开附近设备配对窗口后，用户确认手机入口出现；随后也确认手表入口出现。这支持把“由 Mac 发起开发配对”作为优先处理方法，但不能据此认定某个单独按钮对所有版本都有效。Apple 也明确说明，首次配对时，入口可能要等 Device Hub 开始配对才显示。[Apple：在 Device Hub 中管理设备](https://developer.apple.com/documentation/xcode/managing-your-simulated-and-physical-devices-in-device-hub)

## 2. 在 iPhone 上开启并确认

1. 在 iPhone 上打开 **设置 > 隐私与安全 > 开发者模式**。
2. 打开开关，在提示中轻点“重新启动”。
3. 重启后解锁手机，在确认弹窗中轻点“开启”，并按提示输入设备密码。
4. 保持手机与 Mac 连接，回到 Device Hub 检查是否还提示开启开发者模式。

重启期间，Mac 将手机显示为离线是正常现象。不要因此取消配对；等手机开机、解锁并完成确认后再检查。

## 3. 在 Apple Watch 上开启并确认

先完成手机的开发者模式确认，再处理手表。手表的开关在**手表自身的“设置”App**中，不在手机 Watch App 的隐私页面中。

1. 在 Mac 上保持 Device Hub 的附近设备配对窗口打开，并选中 iPhone 与 Apple Watch 对应的设备类型。
2. 在手表上打开 **设置 > 隐私与安全 > 开发者模式**。如果没有入口，退出这个页面后重新进入。
3. 打开开关，按提示重新启动手表。
4. 重启后解锁手表，轻点“开启”。如果出现“信任”提示，核对设备后确认，并按提示输入手表密码。
5. 如果开发者模式页面列出了待配对的 Mac，选择自己的 Mac，按设备和 Device Hub 显示的提示完成配对；出现配对码时，核对或输入该次显示的代码。

**预期结果：**两台设备上的开发者模式开关均已开启，重启后的确认均已完成，Device Hub 能连接设备且不再提示开启开发者模式。手表不能仅靠手机上的开关启用开发者模式。[Apple：设备端重启与确认步骤](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)

## 4. 检查当前状态，不只看设备列表

在 Mac 的终端中查看设备：

```bash
xcrun devicectl list devices --timeout 20
```

从输出中找到目标手机或手表的标识，然后分别查询详情。将 `TARGET` 替换为对应设备的标识：

```bash
xcrun devicectl device info details --device TARGET --timeout 20
```

判断时同时看连接结果和开发者模式状态：

| 输出或界面 | 如何处理 |
|---|---|
| 成功连接，详情显示 `Developer Mode Status: Enabled` | 当前查询确认开发者模式已开启 |
| `Developer Mode Status: Disabled` | 回设备开启，并完成重启后的确认 |
| `Unable to retrieve complete information` 或无法建立连接 | 后面的详情可能来自缓存，不能当作实时状态 |
| 列表中有 `paired`、`available (paired)` | 只能作为设备发现和配对记录的线索，不能单独证明当前可调试 |
| Device Hub 仍显示 `Enable Developer Mode` | 检查设备重启后的确认是否完成，再刷新连接 |

本次就遇到了缓存误判：重置过的手表无法连接，但详情仍返回旧的 `Enabled` 状态。看到这个字段前，必须先看查询有没有报错。

开发者模式开启不等于 App 已能安装。后续还可能需要完成设备支持组件准备、开发团队选择和代码签名；这些不在本文操作范围内。

## 入口仍未出现时

按现象处理，不要一开始就抹掉手机或手表。

| 现象 | 下一步 |
|---|---|
| Xcode 提示 **Install Required** | 先完成必需组件安装，再打开 Device Hub；仅装命令行工具不能替代完整 Xcode 的设备管理界面 |
| Mac 能识别手机，但手机没有入口 | 解锁手机并处理信任提示；在 Device Hub 中选择手机，再打开 **Pair Nearby Device…**，然后重进手机的“隐私与安全” |
| 手机有入口，手表没有 | 先完成手机重启后的确认；确认手表已与手机完成日常配对，再保持附近设备配对窗口打开，到手表自身设置中检查 |
| 手表重置过，Mac 仍列出原设备 | 把旧条目视为待核实记录。先尝试附近设备配对；只有旧开发配对确实阻碍连接时，才在 Device Hub 中对目标设备执行 **Unpair** 后重新配对 |
| 设备已重启，但 Mac 仍报开发者模式关闭 | 解锁设备，检查是否漏掉重启后的“开启”确认；手机可重新插拔数据线后再查询 |
| 配对窗口一直等待 | 检查设备是否解锁、是否处于同一 Wi-Fi，以及设备上是否有待处理的配对或信任提示 |

Device Hub 中的 **Unpair** 针对与 Mac 的开发配对。不要为修复开发连接，误到 iPhone 的 Watch App 中取消手表的日常配对，更不要把抹掉设备作为常规步骤。

### 可选：用命令行重新发起手机配对

本次在进入附近设备配对窗口前，也执行过以下命令。将 `TARGET` 替换为设备列表中的手机标识：

```bash
xcrun devicectl manage pair --device TARGET --timeout 30
```

命令返回配对成功，不等于已经开启开发者模式。本次没有单独验证这条命令能否让隐藏入口出现；优先使用前面的 Device Hub 步骤，命令行用于辅助排查。

## 验证范围与参考

记录于 2026-11-02。已在 Mac 上检查设备列表、执行手机配对，并打开 Device Hub 的附近设备配对窗口；用户随后确认手机和手表均出现开发者模式入口，并分别开始重启。记录时尚未完成两台设备重启后的实时复核，也未验证 App 安装。

操作依据为 Apple 的[开发者模式说明](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)和[设备配对说明](https://developer.apple.com/documentation/xcode/managing-your-simulated-and-physical-devices-in-device-hub)。界面名称随 Xcode 和系统版本变化时，以当前界面和官方说明为准。

写法参考 [Google Procedures](https://developers.google.com/style/procedures)、[Microsoft 分步操作指南](https://learn.microsoft.com/en-us/style-guide/procedures-instructions/writing-step-by-step-instructions)及 [Apple Style Guide](https://support.apple.com/en-ph/guide/applestyleguide/welcome/web)：标明操作发生在哪台设备上，按执行顺序编号，写出重启后的确认和检查方法，将故障处理放在正常步骤之后。
