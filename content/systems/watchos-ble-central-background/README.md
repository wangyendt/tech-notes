---
type: article
title: Apple Watch：BLE Central 与后台运行配置
description: 从一个 watchOS 与 iOS 双端工程出发，说明手表主动连接手机 GATT 服务、分片传输，以及 Workout、扩展运行会话与 Xcode 后台配置的作用和限制。
tags: [watchOS, iOS, BLE, Xcode, 后台运行]
date: 2026-10-26
updated: 2026-10-26
---

# Apple Watch：BLE Central 与后台运行配置

这里讨论的是 **Apple Watch 主动连接手机、把手腕运动处理结果发送给手机**的方案。手表是 BLE Central，手机是 Peripheral；数据主要由手表写给手机，而不是由手机发通知给手表。

这条链路能够与 watchOS 后台会话结合，但没有一个 Xcode 开关能让普通 Watch App 永久运行。必须分别解决三件事：应用获得什么运行机会、传感器是否继续产生数据、BLE 接收端是否真正收到完整记录。

本文基于匿名化工程的静态核查，未重新编译原工程或新增真机实验。文中的配置建议仍需按文末清单验收。

??? note "核查范围与匿名说明"
    WatchApp、PhoneApp 是角色别名，不是实际 Target 名称。公司、原项目名称、Bundle ID、Team ID、内部地址和原始 UUID 已省略，未复制识别算法代码。

    “当前实现”指源码或配置现状，“建议”不表示已经修改原工程。本文结合 Apple 官方文档解释相关行为，不把静态配置声明当作真机保活结果。

## 1. 角色与连接流程

### Central 不等于数据接收端

| 层次 | 手表 WatchApp | 手机 PhoneApp |
|---|---|---|
| GAP 角色 | Central：扫描、发起连接 | Peripheral：广播、接受连接 |
| GATT 角色 | Client：发现服务、写入特征 | Server：发布服务和可写特征 |
| 当前主要数据方向 | 传感器处理结果 → 写入 | 接收写入 → 重组、解析 |
| 当前实现 | `CBCentralManager`、`CBPeripheral` | `CBPeripheralManager`、`CBMutableService` |

BLE 角色决定发现和连接方式，不决定业务数据只能朝哪个方向流动。这个方案也不是 `WatchConnectivity`，没有通过配套 iPhone 的系统通信通道转发。

Watch-only 应用与独立的 iPhone 应用可以分别运行。`WKWatchOnly` 描述应用包装／安装关系，不是保活权限；Apple Watch 与 iPhone 的系统配对关系，也不等于这条自定义 GATT 连接。

### 首次建立连接

```text
手机蓝牙 poweredOn
  → 创建可写特征和主服务
  → add(service)
  → didAdd 成功后广播 SERVICE_UUID

手表蓝牙 poweredOn
  → 按 SERVICE_UUID 扫描
  → 发现候选手机，停止扫描并连接
  → didConnect
  → discoverServices
  → discoverCharacteristics
  → 检查特征支持预期写入方式
  → 应用级身份／版本确认
  → Ready，开始发送
```

当前实现完成了发现、连接和特征发现，但连接的是**第一个广播约定服务的 Peripheral**，没有应用级身份确认。固定 UUID 不是认证材料；附近另一台测试手机使用相同服务时，也可能被选中。首次连接应让用户确认对象，之后保存已选设备标识，并在重连后核验会话身份和协议版本。

不要把这些状态合成一个绿色“已连接”：

- `poweredOn`：蓝牙可用；
- `isAdvertising`：广播流程启动，不表示手表已经连接；
- `didConnect`：链路已连接，服务和特征可能尚未发现；
- `Ready`：目标特征与业务协议已确认；
- `Receiving`：手机实际收到并接受了有效数据。

当前手机代码在发起广播后就更新界面标志，失败回调才清除。产品实现应以广告启动回调和实际收包状态分别更新界面。

### 已知设备重连

首次发现尽量在两端前台完成，保存 `CBPeripheral.identifier`。后续可以尝试 `retrievePeripherals(withIdentifiers:)` 取得对象，再发起连接；取回对象本身不代表设备已连接或仍在范围内。这个标识不是蓝牙 MAC，也不应当作可信身份。

当前手表在连接失败和断开回调中重新扫描，没有退避、重连超时或显式恢复流程。建议按“蓝牙可用 → 有允许的运行机会 → 尝试已知设备 → 有界重试”的状态机处理，而不是在后台无限扫描。

watchOS 的前台、后台会话和后台刷新有不同的运行机会。Apple 的后台刷新方案面向短时读取已知设备，不保证固定调度间隔。不能直接照搬 iOS 的后台扫描行为，推导出手表能持续冷扫描或维持高频发送。[Apple：连接蓝牙设备到 Apple Watch](https://developer.apple.com/videos/play/wwdc2021/10005/)

## 2. 数据格式、分片与可靠性

### 本项目发送的不是原始 IMU 流

当前连续记录包含时间戳、三个浮点结果和一个移动方向标志；另有离散事件消息。源文件中的部分注释仍使用“四元数”一词，但线上的连续记录实际是下面的布局。

所有多字节数值按 **little-endian** 编码。服务 UUID 和消息标记在新实现中自行约定，下面不复用原工程的标识。

#### 每个分片的外层头部

| 偏移 | 字节 | 字段 | 用途 |
|---:|---:|---|---|
| 0 | 4 | `magic: UInt32` | 区分连续结果和离散事件 |
| 4 | 4 | `frameId: UInt32` | 一条完整业务消息的编号 |
| 8 | 4 | `totalLen: UInt32` | 完整业务负载长度 |
| 12 | 2 | `chunkIndex: UInt16` | 从 0 开始的分片序号 |
| 14 | 2 | `chunkCount: UInt16` | 本消息分片总数 |
| 16 | 可变 | 分片负载 | 业务消息的一部分 |

`magic` 是整数值，不要把注释里的字符顺序直接当成线上的字节顺序。例如整数 `0x12345678` 的 LE 字节为 `78 56 34 12`。

#### 连续结果的完整负载

前 8 字节为 `version(UInt16)`、`batchSize(UInt16)`、`sampleCount(UInt16)`、`reserved(UInt16)`。随后每条记录 **21 字节**，没有结构体对齐填充：

| 记录内偏移 | 字节 | 字段 |
|---:|---:|---|
| 0 | 8 | `timestamp: Float64` |
| 8 | 4 | `x: Float32` |
| 12 | 4 | `y: Float32` |
| 16 | 4 | `z: Float32` |
| 20 | 1 | `moveFlag: Int8`，当前使用 -1、0、1 |

Python 对照格式为 `struct.Struct("<dfffb")`，大小必须为 21。接收端不能用有内存填充的 Swift/C 结构体直接替代线格式；方向标志也不能误读为无符号 255。

#### 离散事件的完整负载

| 偏移 | 字节 | 字段 |
|---:|---:|---|
| 0 | 2 | `version` |
| 2 | 2 | UTF-8 名称字节数 `N` |
| 4 | 4 | 保留字段 |
| 8 | 8 | 事件对应的传感器时间戳 |
| 16 | 8 | 置信度 |
| 24 | N | UTF-8 名称 |
| 24 + N | 1 | 状态标志 A |
| 25 + N | 1 | 状态标志 B |

最小完整长度为 `26 + N`，`N` 是字节数，不是字符数。手机按消息类别分别解析，再更新界面或转发；UDP 中继是下一条独立链路，不能把“BLE 接收成功”当成“电脑已收到”。

### 写入长度不是一个固定 MTU 常量

发送前查询 `maximumWriteValueLength(for: .withoutResponse)`，记返回值为 `W`。这是当前允许的**特征写入值长度**，不是直接返回底层 ATT MTU。16 字节自定义头部也占用这段空间：

```text
C = W - 16                 # 每片最多承载的业务字节
L = 8 + 21 × sampleCount   # 连续结果的完整负载
K = ceil(L / C)            # 分片数；前提 W > 16
```

当前代码用 `max(1, W - 16)`；若 `W <= 16`，生成的分片仍可能超过允许长度。正确处理是拒绝该分片配置或换协议，不是强行塞入一个字节。

以 10 条一批为**计算示例，不是真机测速结果**：

| `W` | `C` | 218 字节负载需要的分片 |
|---:|---:|---:|
| 20 | 4 | 55 |
| 185 | 169 | 2 |

如果请求 200 条／秒、每批 10 条，前一种情况会尝试约 1100 次分片写入／秒。请求频率、实际传感器频率和链路吞吐必须分开测量；提高 batch size 只能改变开销与等待延迟，不能绕过系统流控。

### 当前可靠性缺口

| 当前实现 | 后果 | 建议 |
|---|---|---|
| 缓冲达到批大小后先清空，再检查连接 | 未连接的批次直接丢弃 | 明确实时丢弃还是可靠缓存；记录丢弃计数 |
| 逐片调用 `.withoutResponse`，未检查发送可用性 | 不能据调用次数判断手机接收条数 | 有界发送队列、平台流控、接收计数 |
| 停止时没有显式发送不足一批的尾部 | 最后一小段记录可能留在缓冲 | 结束时 flush，并记录是否完成 |
| 手机忽略 `chunkIndex`，假定按序直接拼接 | 无法识别应用层重复、错片和跨会话混入 | 按序号存储，检查字段一致性及完整性 |
| 重组表只按 `frameId` 索引 | 多手表从相同编号开始时可能混帧 | 加入 Central 身份、连接会话和消息类别 |
| 未限制 `totalLen`、并发帧数量等 | 异常长度可占用过多内存 | 限制帧长、分片数和缓存；独立回收超时帧 |
| 特征声明 `.write`，却未实现相应响应流程 | 不能宣称已支持可靠的带响应写入 | 按 ATT 请求回调约定校验并响应 |

无响应写入应结合 `canSendWriteWithoutResponse` 和 `peripheralIsReady(toSendWriteWithoutResponse:)`。下面只是发送泵片段，队列上限、断开策略和业务确认仍需实现：

```swift
func drainPendingWrites() {
    guard let peripheral, let writeCharacteristic else { return }
    while peripheral.canSendWriteWithoutResponse && !pendingChunks.isEmpty {
        let chunk = pendingChunks.removeFirst()
        peripheral.writeValue(chunk, for: writeCharacteristic, type: .withoutResponse)
    }
}

func peripheralIsReady(toSendWriteWithoutResponse peripheral: CBPeripheral) {
    drainPendingWrites()
}
```

生产代码宜使用有界队列而非反复 `removeFirst()`，并让连接状态和队列操作串行化。ATT 有响应写入也不等于业务落盘确认；需要可靠事件交付时，应另外定义应用级确认与幂等规则。[Apple：发送流控](https://developer.apple.com/documentation/corebluetooth/cbperipheral/cansendwritewithoutresponse)、[ATT 写入回调](https://developer.apple.com/documentation/corebluetooth/cbperipheralmanagerdelegate/peripheralmanager(_:didreceivewrite:))

### 时间戳必须带清楚的时钟定义

手表当前把 `CMDeviceMotion.timestamp` 的开机计时转换到 `CFAbsoluteTime`：

```text
sensorAbsoluteTime = CFAbsoluteTimeGetCurrent()
                   - (systemUptime - motion.timestamp)
```

因此连续记录的时间是 **2001-01-01 参考纪元的秒数**，不是 Unix 毫秒。手机转发时另加的批次时间使用 Unix 秒，两列不能直接相减。转换可用：

```swift
let unixSeconds = Date(timeIntervalSinceReferenceDate: wireTimestamp)
    .timeIntervalSince1970
```

事件时间戳从处理器回调传来，集成时也要核对其时钟契约。建议同时保留传感器单调时钟、发送序号、手机接收时间和会话 ID；跨设备测延迟还需要时钟对齐，不能仅凭两台设备都返回 `Double` 时间就认定同步。

## 3. 先选择运行机制，再配置 Xcode

### 哪些机制适合持续采集

| 机制 | 能提供什么 | 不能据此保证什么 |
|---|---|---|
| 普通前台运行 | 用户操作期间采集、处理与 BLE 通信 | 放下手腕、切换应用后无限运行 |
| `HKWorkoutSession` | 真实运动记录期间的后台执行机会 | 通用光标控制器可伪装成运动；永不被系统终止 |
| `WKExtendedRuntimeSession` | 指定活动类别的一段延长运行时间 | 任意业务类别、无限续期 |
| Background App Refresh | 系统调度的短时刷新任务 | 固定频率、连续高采样率 |
| 后台 BLE 特征监控 | 有意义的外设事件触发处理机会 | 用密集通知代替常驻 CPU |

真实运动应用可以选择 Workout；真实复健、正念等活动可按业务选扩展会话。**普通手势遥控器若不属于这些用途，就不能仅为后台执行而选择一个无关的活动类型。** 后台能力按其声明用途使用，不是通用保活许可。[Apple：后台会话](https://developer.apple.com/documentation/watchkit/enabling-background-sessions)、[App Review 2.5.4](https://developer.apple.com/app-store/review/guidelines/#software-requirements)

watchOS 9 引入的后台特征监控由手机／外设更新 Notify 特征，手表订阅后获得事件处理机会；它有系统预算，面向对用户有意义的及时事件。当前工程主要是**手表主动写入**，没有这条 Notify 订阅链路，不能把该特性当成现有高频采样代码的保活依据。[Apple：后台蓝牙事件](https://developer.apple.com/videos/play/wwdc2022/10135/)

### 扩展运行的类别和上限

| `WKBackgroundModes` 值 | 活动类别 | 运行类型 | 文档给出的时限 |
|---|---|---|---|
| `self-care` | 自我护理 | Frontmost | 10 分钟 |
| `mindfulness` | 正念 | Frontmost | 1 小时 |
| `physical-therapy` | 物理治疗 | Background | 1 小时 |
| `alarm` | 智能闹钟 | Background，可调度 | 30 分钟 |

Frontmost 可以在屏幕关闭时继续运行，但用户按数码表冠离开、切换应用后不能按相同规则继续。Background 类型允许活动期间切到其他界面，也仍有时限和资源限制。类别应匹配实际业务，不是挑最长的一项。[Apple：扩展运行会话](https://developer.apple.com/documentation/watchkit/using-extended-runtime-sessions)

当前配置选择 `mindfulness` 并同时声明 `workout-processing`。这个声明组合本身允许存在：**扩展类别只能选一个，但可以与 Workout 模式并存**。它不代表两个会话必须同时启动，也不代表可以叠加成无限运行。[Apple：WKBackgroundModes](https://developer.apple.com/documentation/bundleresources/information-property-list/wkbackgroundmodes)

## 4. Xcode 配置：逐项核对

### 4.1 找到真正执行代码的 Target

在 Project navigator 选项目，再在 **TARGETS** 里选实际的 Watch App。不要只选项目级设置、共享 Framework、测试 Target 或 iOS 包装容器。

现代单 Target watchOS 工程的代码与资源在 Watch App 内；旧文档中的 WatchKit Extension 对应旧工程结构，不能机械照搬位置。[Apple：单 Target watchOS 工程](https://developer.apple.com/documentation/watchos-apps/migrating-to-a-single-target-watchos-app)

本次文件核查结果如下；这些是原工程值，不是建议所有新工程照抄的最低版本：

| 项目 | WatchApp | PhoneApp |
|---|---|---|
| SDK | `watchos` | `iphoneos` |
| 最低系统 | watchOS 11.2 | iOS 18.5 |
| Device Family | `4` | `1,2` |
| Swift Language Version | `5.0` | `5.0` |
| Signing Style | Automatic | Automatic |
| Generate Info.plist File | YES | YES |
| Info.plist File | 有独立文件 | 有独立文件 |
| Code Signing Entitlements | 指向 Watch entitlements | 未见独立文件 |
| Watch-only | YES | 不适用 |

另有一个 iOS Watch 容器 Target，它不等于手机 Peripheral 应用。共享 Framework 的 watchOS 最低版本低于 WatchApp，也不能据此认定 WatchApp 支持该更低版本。

### 4.2 General 与 Signing & Capabilities

1. **General → Deployment Info**：选择目标手表实际支持的最低 watchOS 版本，确认依赖 Framework 也有对应设备切片。Deployment Target 不是保活参数。
2. **Signing & Capabilities → Team**：使用有权部署该应用的开发团队，保持 Bundle Identifier 唯一；匿名示例不包含实际标识。
3. 使用自动签名时，让 Xcode 为正确的 Watch App App ID 配置所需能力；手工签名时检查 provisioning profile 是否匹配这些能力。
4. Debug、Release 都核对，不要只改当前选中的一个 Configuration。
5. 确认真正签进成品的 entitlement；源码文件里写了 `true`，不等于描述文件和最终签名已允许它。

`SKIP_INSTALL` 影响打包／安装产品，不控制运行时。当前 Watch Target 为 YES；如果 Archive 缺少产品应单独排查分发配置，而不是把它改成某值当作保活修复。Swift 优化等级、后台队列 QoS、Framework 的可分发构建选项也不是后台运行授权。

### 4.3 Info.plist 的两处来源

当前工程同时使用：

- `GENERATE_INFOPLIST_FILE = YES`；
- `INFOPLIST_FILE` 指向的文件；
- Build Settings 中的 `INFOPLIST_KEY_*` 注入项。

因此只看磁盘上的 plist 文件会漏掉权限文案；只看 Target → Info 也可能漏掉自定义文件的数组。最终以**构建产物里实际的 Info.plist**为准。一个键只维护一个明确来源，尤其不要在两处放不同的 `UIBackgroundModes` 数组，靠猜测判断它们会相加。

### 4.4 当前后台声明与推荐处理

| 键／能力 | 当前 Watch 配置 | 作用与处理 |
|---|---|---|
| `WKBackgroundModes` | `mindfulness`、`workout-processing` | 两类声明可并存，实际启动哪类由真实业务决定 |
| `UIBackgroundModes` | 只有 `audio` | 未见 `bluetooth-central`；如需对应后台 BLE 事件，应在实际 Watch bundle 中补齐声明 |
| `com.apple.developer.healthkit` | true | 允许请求 HealthKit 授权，不能替用户授权 |
| `com.apple.developer.healthkit.background-delivery` | true | 面向 Observer Query 后台交付，不等于 Workout 保活 |
| `NSBluetoothAlwaysUsageDescription` | Build Settings 已提供 | 解释为何需要蓝牙；并不承诺 Always 常驻 |
| `NSHealthShareUsageDescription` | 已提供 | 读取健康数据用途 |
| `NSHealthUpdateUsageDescription` | 已提供 | 写入健康数据用途 |
| `NSMotionUsageDescription` | 当前核查未见 | 按实际 Core Motion API／SDK 补充运动数据用途说明 |

这里“未声明 `bluetooth-central`”表示没有声明这类后台蓝牙执行模式，**不能反过来推断在活动 Workout 内一定无法通信**。Apple 对 watchOS 后台蓝牙的说明要求把该值加到 Watch App 的 `UIBackgroundModes`；仅改 iPhone Target 的 Capability 不会代替它。[Apple：watchOS BLE 配置](https://developer.apple.com/videos/play/wwdc2022/10135/)

两个数组不要混淆：

```text
WKBackgroundModes → workout-processing / mindfulness 等会话类别
UIBackgroundModes → bluetooth-central / audio 等相关能力
```

### 4.5 真实 Workout 路径

在实际 Watch Target 的 **Signing & Capabilities** 中：

1. **+ Capability → HealthKit**。
2. **+ Capability → Background Modes → Workout processing**。
3. 在 Info／自定义 plist 中核对 `WKBackgroundModes` 的原始值是 `workout-processing`。
4. 如采用后台 BLE 回调能力，在 Watch 的 Info.plist 中加入 `UIBackgroundModes = [bluetooth-central]`。Xcode 是否提供对应图形选项会随模板变化，原始键值不能省略核验。
5. 填写真实用途的健康权限文案，再在代码中请求所需的最小数据类型。

下面是**业务确属运动记录时**的配置片段，未列 Bundle ID、版本、启动项等由模板维护的基础键：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSBluetoothAlwaysUsageDescription</key>
    <string>连接用户选择的手机并传输本次运动记录。</string>
    <key>NSHealthShareUsageDescription</key>
    <string>读取用户授权的本次运动心率与活动数据。</string>
    <key>NSHealthUpdateUsageDescription</key>
    <string>按用户选择保存本次体能训练记录。</string>
    <key>NSMotionUsageDescription</key>
    <string>在用户开始记录后采集手腕运动数据。</string>
    <key>UIBackgroundModes</key>
    <array><string>bluetooth-central</string></array>
    <key>WKBackgroundModes</key>
    <array><string>workout-processing</string></array>
</dict>
</plist>
```

对应的基础 HealthKit entitlement：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.developer.healthkit</key><true/>
</dict>
</plist>
```

Workout 仍要由代码创建并真正进入运行态。请求写入 Workout 的权限是该路径的一部分，读取心率等则按实际使用申请。授权请求的完成回调 `success` 不表示所有读取权限都被授予；HealthKit 不向应用直接暴露某些读取权限被拒绝的状态。[Apple：运行 Workout](https://developer.apple.com/documentation/healthkit/running-workout-sessions)、[健康数据隐私](https://developer.apple.com/documentation/healthkit/protecting-user-privacy)

后台音频／触觉提示确有需要时，再按 Workout 文档配置 `audio`。当前 Watch 代码存在触觉调用，不能仅因没有音乐播放器就一概判断该声明多余；但 `audio` 也不能替代 Workout 或 BLE 配置。

### 4.6 HealthKit 的 Background Delivery 不是另一个保活开关

Xcode 的 **HealthKit → Background Delivery** 会添加 `com.apple.developer.healthkit.background-delivery`，用于配合 `HKObserverQuery` 和 `enableBackgroundDelivery` 接收数据变化。

当前工程有该 entitlement，但未见对应 Observer Query 注册路径。它不能让 `Timer`、Core Motion 或 BLE 发送循环无限运行；只为 Workout Session 延长运行而额外勾选它，没有解决另一层问题。[Apple：HealthKit Background Delivery](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.healthkit.background-delivery)

### 4.7 扩展运行路径

若业务确属正念、护理或复健，在 **Background Modes → Session Type** 选择**一个**合适类别，并核对 `WKBackgroundModes`。例如，真实正念活动可以配置：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSBluetoothAlwaysUsageDescription</key>
    <string>连接用户选择的手机并传输本次活动数据。</string>
    <key>UIBackgroundModes</key>
    <array><string>bluetooth-central</string></array>
    <key>WKBackgroundModes</key>
    <array><string>mindfulness</string></array>
</dict>
</plist>
```

这不要求额外启动一个没有实际用途的 Workout。正念类型也不允许用户离开应用后按 Background 类型继续运行。

`WKExtendedRuntimeSession.start()`／调度必须在 App 的 `.active` 状态调用。异步授权或初始化完成时，用户可能已经离开界面，因此在调用前要重新判断状态；不能因为最初的按钮点击发生在前台，就认为稍后的回调仍在前台。[Apple：active 状态要求](https://developer.apple.com/documentation/watchkit/wkextendedruntimesessionerrorcode/mustbeactivetostartorschedule)

会话将到期时应收尾；失效后先区分用户停止、超时、资源超限和其他错误。`invalidate()` 后原对象不能再次启动，需要新对象，也不意味着可以从任意后台状态立即重开。[Apple：结束扩展会话](https://developer.apple.com/documentation/watchkit/wkextendedruntimesession/invalidate())

### 4.8 蓝牙、运动与网络隐私键

| 配置 | BLE／保活是否必需 |
|---|---|
| `NSBluetoothAlwaysUsageDescription` | 使用蓝牙接口应声明，系统授权仍由用户决定 |
| `NSBluetoothPeripheralUsageDescription` | 当前较新的 iOS 部署目标不因“手机是 Peripheral”就必须使用这个旧键；它与历史版本兼容有关 |
| `NSMotionUsageDescription` | 按实际 Motion API 要求声明；尤其包含计步、运动分类、传感器记录等受保护接口时核对，不能把所有 Motion API 的授权行为混为一谈 |
| `NSLocalNetworkUsageDescription` | 手机要将数据转发局域网电脑时单独配置；纯 BLE 不是本地网络通信 |
| `NSBonjourServices` | 只有实际做 Bonjour 服务发现才声明对应类型 |
| `NSAllowsArbitraryLoads` | 不是蓝牙或保活要求；不要为复用旧调试配置而默认放开 HTTP |

当前工程还含局域网服务发现与 HTTP 调试配置，它们属于模型／网络功能，不应混入最小 BLE 配置。权限文案应描述用户可理解的数据用途，而不是“为了保活”。[Apple：蓝牙隐私键](https://developer.apple.com/documentation/bundleresources/information-property-list/nsbluetoothalwaysusagedescription)、[运动隐私键](https://developer.apple.com/documentation/bundleresources/information-property-list/nsmotionusagedescription)

### 4.9 Scheme、真机和系统设置

- **Product → Scheme → Edit Scheme → Run → Info**：检查 Build Configuration；最终验收使用 Release。
- 关闭 **Debug executable**，并补做从设备图标启动的测试。当前两个 Scheme 文件的 LaunchAction 已配置为 Release，Debugger 标识为空，但这仍不是完成真机验收的证据。
- 选择真实 Apple Watch 运行目标。模拟器上的 BLE、HealthKit 和后台行为不能替代真机结果。
- 开发安装所需的 Developer Mode 只影响开发部署，不提供额外后台权限。
- 记录用户的后台刷新、低电量模式、权限和其他 Workout 状态，不在测试中悄悄改变条件。
- “返回时钟”设置、`isIdleTimerDisabled` 和屏幕常亮不能代替后台运行授权。手机关闭自动锁屏，也不妨碍用户手动锁屏。

## 5. 生命周期代码比勾选项更容易影响结果

### 会话和采样要由应用级对象拥有

建议让一个长期存活的协调器分别管理：

```text
用户活动状态：idle → authorizing → starting → running → ending → stopped/failed
采样状态：    stopped / collecting / interrupted
BLE 状态：   unavailable / discovering / connecting / ready / disconnected
发送状态：   idle / draining / backpressured / failed
```

不能只用一个布尔值表示全部状态。`CBCentralManager`、`CBPeripheral`、Workout Session、Builder 和采样管理器都需要在活动期间被强引用保留。

当前主页面在 `onAppear` 启动 IMU、在 `onDisappear` 停止。某些页面切换会因此停止采样，即使 Workout 还在运行；熄屏是否触发具体视图事件要看日志，不能一概认定。测试页面还拥有另一份 IMU 管理器，若同时实例化，也可能产生多份连接管理器。跨页面的活动应由应用级对象统一拥有，而不是依赖某个页面始终存在。

### 当前启动和停止链路的风险

当前代码的 `HKWorkoutConfiguration` 使用 `.other` 活动类型、`.unknown` 位置类型；请求读取心率、活动能量和 Workout，写入 Workout。这些是运行时代码参数，不是 Xcode 勾选项，`.other` 也不是把任意遥控任务变成真实运动的许可。

SwiftUI 工程可以在 App 层长期持有协调器，需要应用代理时通过 `@WKApplicationDelegateAdaptor` 接入。不要在代理、主页面和测试页面各自创建一套采样／会话对象，再指望某一个实例的状态代表全部工作。

| 源码现状 | 需要调整的地方 |
|---|---|
| `applicationDidBecomeActive` 自动启动 Workout | 改为用户明确开始真实活动；回前台只同步状态，不重复创建 |
| 初始化时发起异步授权，随后即可尝试启动 | 等待授权流程结束，并处理取消、写入权限与错误 |
| 只用 `isSessionRunning` 防重入 | 增加 `authorizing/starting/ending` 等中间态，防止异步重入 |
| Workout 开始收集后再启动扩展会话 | 先确认是否需要第二种会话，且异步回调时仍满足 active 条件 |
| `willExpire` 创建新扩展会话 | 到期时收尾，不把它当作无限续期入口 |
| 每次 `didInvalidate` 都延迟一秒重开 | 用户主动停止也可能被重新启动；必须有停止意图和失效原因判断 |
| 清理依赖 `applicationWillTerminate` | 进程被终止时未必得到清理机会，需持久状态及适当恢复设计 |
| Workout 结束后仅调用 `endCollection` | 明确按用户选择保存或丢弃，并处理结束失败，不留下含糊状态 |

当前已经有对“正在运行”的检查和错误日志，但未见完整的 Activity 恢复路径。若产品需要 Workout 恢复，应按目标系统的 HealthKit 恢复接口重新取得活动会话并绑定代理；不能在重启时盲目新建第二场。原实现没有因为写了 `start()` 就得到无限后台运行。

结束时应同时处理：停止产生新记录、尾批发送或明确标记未发送、结束业务活动、保存／丢弃 Workout、停止扩展会话、更新界面。出错或系统打断时也要保留“已停止／结果未确认”的区别。

## 6. 手机 Peripheral 的前后台配置

### iPhone 的最小 BLE 声明

手机 Target 的 **Signing & Capabilities → Background Modes** 选择 Peripheral 对应能力，最终原始值应是 `bluetooth-peripheral`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSBluetoothAlwaysUsageDescription</key>
    <string>向用户选择的手表提供连接服务并接收活动数据。</string>
    <key>UIBackgroundModes</key>
    <array><string>bluetooth-peripheral</string></array>
</dict>
</plist>
```

当前手机确有该后台模式，但它提供的是处理 BLE 事件的机会，不是任意 CPU／UDP 循环的永久运行资格。后台广播也有变化：本地名称不会正常广播，服务 UUID 进入特殊 overflow 区域，广播频率可能降低。

Apple 的 iOS 指南将 overflow 发现描述为由显式扫描对应 UUID 的 iOS 设备完成。**不能仅凭这段说明，就保证 watchOS 能冷发现一台已经后台化的 iPhone。** 应分别验证“前台建连后手机锁屏”和“手机已经在后台时重新发现”，尤其是断连后的恢复。[Apple：iOS 后台 BLE](https://developer.apple.com/library/archive/documentation/NetworkingInternetWeb/Conceptual/CoreBluetooth_concepts/CoreBluetoothBackgroundProcessingForIOSApps/PerformingTasksWhileYourAppIsInTheBackground.html)

当前手机程序还关闭了自动锁屏，并尝试播放循环静音音频。前者不是后台权限；后者不应作为正式 BLE 保活方案，也不能仅凭调用 `play()` 就认定成功。公开实现应按真实业务使用音频能力，并单独验证后台 UDP 中继，而不是依赖不可见音频维持整个进程。[Apple：后台服务用途要求](https://developer.apple.com/app-store/review/guidelines/#software-requirements)

iPhone 可以评估 Core Bluetooth 的状态保存／恢复能力，但需要持久恢复标识和对应回调，恢复服务与广播状态；用户强制退出、系统终止和蓝牙关闭不是同一种事件，不能承诺全部自动复活。当前双端实现未见完整状态恢复处理。

### Android 手机的迁移范围

本次实际代码是 iPhone Peripheral，**没有据此验证 Android 后台服务或所有品牌手表**。若手机端改成 Android，手表端 GATT 客户端角色可以保留，手机侧需另实现：

1. 检查硬件和系统是否支持 BLE 广播及 GATT Server。
2. 使用 `BluetoothLeAdvertiser` 广播服务 UUID，以 `BluetoothGattServer` 发布相同线协议的可写特征。
3. Android 12+ 按操作申请 `BLUETOOTH_ADVERTISE`、`BLUETOOTH_CONNECT` 等运行时权限；只有实际扫描才另考虑 `BLUETOOTH_SCAN`，不能把 iOS plist 当成 Android 权限。
4. 处理写入请求、响应、连接身份与多 Central 的重组隔离。
5. 为持续接收单独设计符合该 Android 版本规则的前台服务、通知和电源管理策略，并进行锁屏／杀进程测试。

这些是迁移清单，不是已实现结果。[Android：蓝牙权限](https://developer.android.com/develop/connectivity/bluetooth/bt-permissions)、[GATT Server](https://developer.android.com/reference/android/bluetooth/BluetoothGattServer)

## 7. 怎样验证配置确实进入了安装包

先看实际 Build Settings。下面均为通用命令模板，不包含原工程标识：

```bash
xcodebuild -project PROJECT.xcodeproj -scheme WATCH_SCHEME \
  -configuration Release -showBuildSettings \
  | grep -E 'SDKROOT|WATCHOS_DEPLOYMENT_TARGET|INFOPLIST_FILE|GENERATE_INFOPLIST_FILE|CODE_SIGN_ENTITLEMENTS'
```

对自己构建得到的真实 Watch App 包检查，不要选错 iOS 容器：

```bash
WATCH_APP="BUILD_DIR/WatchApp.app"
plutil -p "$WATCH_APP/Info.plist"
plutil -extract UIBackgroundModes json -o - "$WATCH_APP/Info.plist"
plutil -extract WKBackgroundModes json -o - "$WATCH_APP/Info.plist"
codesign -d --entitlements :- "$WATCH_APP"
```

检查结果至少包括：

- `CFBundleSupportedPlatforms` 指向 WatchOS；
- 最终的两个后台模式数组与选定方案一致；
- 蓝牙／健康用途说明已展开，非空且描述真实业务；
- 签名中的 HealthKit entitlement 与描述文件一致；
- Release 和设备实际安装的构建对应，不是拿旧包验证新配置。

不要公开完整 provisioning profile、签名标识或带设备信息的日志。本文附带一个[只读静态检查器](examples/audit_watch_bundle.py)，示例调用为：

```bash
python3 audit_watch_bundle.py "BUILD_DIR/WatchApp.app" --mode workout
# 或真实正念活动：--mode mindfulness
```

它读取成品 plist 和签名 entitlement，不修改应用；检查通过也明确返回 `runtime_verified: false`。它不能检测用户是否授权、当前是否有运行中的 Workout、后台是否持续采样，不能替代后面的运行测试。该脚本通过合成配置单元测试，未对本次原工程的构建产物作运行认证。

## 8. 真机保活与数据交付验收

至少把下面的实验分开做。**本文没有将它们记为已通过。**

| 测试 | 要观察的证据 |
|---|---|
| 两端前台首次连接 | 服务、特征发现完成；手机有效记录计数上升 |
| 手表放下手腕／屏幕熄灭 | 会话状态、Core Motion 计数、手机接收计数均继续变化 |
| 手表按表冠离开／切到其他 App | 与选定会话类型的预期一致；不把 Frontmost 当 Background |
| 手机锁屏 | 已建连接的写入接收和持久化是否继续 |
| 手机先在后台，再尝试发现 | 单独验证后台广播限制，不用前台建连结果替代 |
| 离开蓝牙范围后返回 | 有界重连、正确会话隔离、断开期间丢弃数可解释 |
| 用户主动结束 | 采样和会话确实停止，失效回调不把活动重新启动 |
| 权限拒绝／蓝牙关闭／低电量 | 状态与错误可见，不一直显示“正常采集中” |
| 第二个真实 Workout 启动／系统中断 | 不假定原会话继续，记录状态变化并妥善结束或恢复 |
| 多手表同时发送 | 无跨 Central 混帧，不把单表成功解释为无限并发 |
| 超过所选扩展会话时限 | 正确收尾，不把一秒重试日志算成运行续期成功 |
| 离开 Xcode 调试环境重测 | 从设备图标启动，记录硬件、OS、构建和电量条件 |

每轮至少记录：会话 ID、App 状态变化、Workout／扩展会话状态、实际采样数、产生的业务帧、入队／丢弃／发送计数、手机成功重组帧、重复／超时／缺片计数，以及传感器时间和手机接收时间。

真正支持“熄屏后仍可采集”的证据应是熄屏期间仍有新的样本序号，并且接收端读回对应记录；“界面没退出”“蓝牙图标还在”“定时器日志持续打印”都不足以单独证明整条链路正常。
