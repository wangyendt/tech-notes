---
type: article
title: Android 蓝牙 HCI 日志：文件采集与 btsnoop TCP 流
description: 说明 HCI 能观察和不能观察的数据、抓包与业务解析的区别，以及 btsnoop 文件、诊断包和 8872 TCP 出口的适用条件。
tags: [Android, 蓝牙, HCI, btsnoop, TCP]
date: 2026-11-02
updated: 2026-11-02
---

# Android 蓝牙 HCI 日志：文件采集与 btsnoop TCP 流

排查蓝牙通信时，应用输出的“连接成功”日志往往不足以解释数据是如何传输的。HCI snoop 日志记录手机蓝牙协议栈与蓝牙控制器之间的交互，可以用于分析命令、事件和数据包。部分 Android 实现还通过本机 `127.0.0.1:8872` 实时输出这些记录。

这个端口是特定蓝牙实现的调试出口，不是 Android 通用日志接口，也不是所有手机都提供的稳定公共 API。使用前必须确认系统提供出口、当前进程可访问、日志包含所需数据；安装 Shizuku 不能代替这些条件。

## 正常 BLE 通信、旁路记录和 8872 输出口

开发一个通过 BLE 收发数据的 App 时，不需要在“HCI snoop”和“8872”之间选择。**HCI 是通信接口，HCI snoop 是对接口上的通信做旁路记录，8872 则是某些系统提供的记录输出口。** 后两者都不是正常 BLE 业务传输必须经过的服务。

HCI 是 Host Controller Interface，即主机控制器接口。这里的 Host 是运行蓝牙协议栈的手机系统，Controller 通常是蓝牙芯片。以下以普通 Android BLE 收发路径为例：上下双向箭头表示正常业务通信，向右的分支表示系统对经过的包做调试记录，不是把业务数据改道到 TCP。

```text
你的 App
   ↕ 普通 BLE API
Android 蓝牙协议栈
   ↕
HCI 通信接口 ──启用抓包时──→ HCI snoop 旁路记录
   ↕                           ├─→ 日志文件等出口
手机蓝牙控制器                  └─→ 8872 TCP 出口（若已启用）
   ↕ 无线链路                           ↓ 客户端连接并读取
对方设备                           调试工具 / 自己的接收器
```

文件与 TCP 可以是同一批包记录的不同输出方式；图中的 TCP 分支不表示先读取已落盘的日志文件，也不表示存在文件就一定存在端口。系统是否记录、记录哪些内容以及提供哪些出口，取决于蓝牙实现和配置。[AOSP 包记录与输出实现](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/745ee92b87ed62b5a8a1bac47d5df8cad623bf59/system/gd/hal/snoop_logger.cc#1188)

### 三种配置情况下，业务链路不变

假设 App 的蓝牙权限、连接和收发代码本来就能正常工作，下表比较的是日志配置，不是三种 BLE 发送方式：

| 手机的配置 | 正常 BLE 收发 | HCI snoop 记录 | 8872 输出 |
|---|---|---|---|
| ① 未开启完整 HCI 抓包 | 不依赖完整抓包开关，仍按正常路径收发 | 不保证有完整负载；系统可能仅保留有限诊断记录 | 不能仅据此判断端口状态，更不能假定能读到完整数据 |
| ② 已开启 HCI 抓包，但系统未提供或未启用 TCP 出口 | 按正常路径收发，不需要 TCP 出口 | 可记录符合配置的包，通过系统提供的文件等路径获取 | 没有可用的该出口 |
| ③ 已开启 HCI 抓包，且系统已提供并启用 8872 出口 | 仍按正常路径收发，不改走 TCP | 可记录符合配置的包 | 获准访问的接收程序连接后，可读取系统输出的记录 |

这是配置关系说明，不是三组真机测试。第二、三种情况仍可能受到过滤、截断或记录丢失的影响；第三种还要求读取权限允许。未开启完整抓包不等于系统完全没有诊断记录，开启抓包也不等于 TCP 出口已启用。[Android HCI 日志配置说明](https://source.android.com/docs/core/connect/bluetooth/verifying_debugging)

对 App 开发者而言，只需实现正常 BLE 通信，无需为系统抓包额外调用“发送到 8872”的接口。若目标是开发一个读取日志的工具，才需要另外实现 TCP 接收和 btsnoop 解析，或使用已有调试工具。**关闭日志记录、没有 8872 端口或没有客户端连接，都不意味着正常 BLE 通信必须停止。**

## HCI 日志不是 logcat

HCI snoop 的观察点位于手机蓝牙协议栈与控制器之间，不是直接监听周围所有设备的无线电信号，也不是读取所有 Android 系统日志。

| 机制 | 记录内容 | 常见查看方式 |
|---|---|---|
| logcat | 系统和应用写入日志缓冲区的消息，例如异常、状态和调试文字 | `adb logcat`、Android Studio |
| HCI snoop | 本机蓝牙主机与控制器交换的命令、事件和数据包 | btsnoop 文件、Wireshark、btmon |
| 系统诊断包 | 汇集多类诊断信息，可能包含蓝牙日志或其内存记录 | 导出后按内容提取 |

logcat 读取的是 `logd` 管理的日志缓冲区；btsnoop 则保存蓝牙包记录。蓝牙组件可以同时向 logcat 写状态消息、向 snoop 日志写包，但两者不是同一条流。[Logcat 文档](https://developer.android.com/tools/logcat)、[AOSP 蓝牙调试文档](https://source.android.com/docs/core/connect/bluetooth/verifying_debugging)

因此，可以把 btsnoop TCP 理解为“实时接收蓝牙 HCI 调试数据的一种方式”，不能理解为“从 Android 所有调试日志中恰好筛出蓝牙信息”。它不只面向 BLE，也可能记录经典蓝牙的 HCI 交互；实际覆盖哪些包取决于实现、传输路径及过滤配置。它不包含通用 Wi-Fi、文件操作或应用业务日志。

## HCI 能看到哪些信息，不能看到哪些信息

判断范围的依据是“信息是否经过本机 Host 与 Controller 之间的接口”，而不是“它是否与蓝牙有关”。下表描述的是 HCI 层可能观察到的内容；要在日志中实际看到，还要求采集已开启、记录未被过滤或截断、读取链路正常。

| 信息 | 在 HCI 日志中的可见范围 |
|---|---|
| 主机发给控制器的命令，以及控制器返回的事件 | 可以记录实际交换的 HCI 命令和事件，例如连接、断开及状态报告；不是控制器内部执行过程的逐步追踪 |
| 常规 BLE 特征值读写、通知和指示 | 相关 ATT 数据通常承载在 HCI ACL 数据包中，可经 L2CAP 重组后分析；日志里不是直接出现 App 的回调对象 |
| 经典蓝牙的业务数据 | 经过 HCI 的数据可能被记录，再按对应上层协议解析；不能仅因耳机正在播放，就断言音频负载一定完整经过所观察的路径 |
| 扫描得到的广播信息 | 能看到控制器实际通过 HCI 上报的广播报告；扫描窗口、重复过滤等会影响上报，不等于每个空中广播包都有一条记录 |
| 无线重传、空中确认和 LL/LMP 控制交互 | 通常由控制器处理，不会逐包原样交给 Host；可能看到相应结果或状态事件，但不是完整空中轨迹 |
| 控制器内部或绕过该 HCI 采集点的数据路径 | 不能假设标准 HCI snoop 会覆盖，需要另外确认硬件与厂商实现 |
| 周围其他设备彼此之间的通信 | 不能把本机 HCI 日志当作通用空中嗅探器；收到它们的广播报告，也不意味着能看到它们之间的连接数据 |
| App 内部变量、云端响应、未通过蓝牙传输的测量结果 | 不会仅因启用 HCI 日志而出现；它们不经过这个观察点 |

这个范围来自蓝牙 Host/Controller 的分层。无线链路上的一次业务传输可能涉及多次空中发送，而 HCI 只体现主机与控制器之间的数据交付；因此不能用 HCI 包数直接代替空中包数或无线重传次数。[Bluetooth Core 6.0 架构与可靠性说明](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-60/out/en/architecture,-change-history,-and-conventions/architecture.html)、[HCI 功能规范](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-60/out/en/host-controller-interface/host-controller-interface-functional-specification.html)

HCI 日志与 `8872` 也不是两份相互补充的数据源。后者只是某些系统输出前者的通道，不会增加观察层次，也不会补回未记录、被过滤或采集前已经发生的通信。

## 抓到字节，不等于已经读懂业务

日志中的数据需要先按 HCI、L2CAP 和实际使用的上层协议重组，才可能还原为业务消息。即使 Wireshark 已识别出一次 ATT 通知，特征值仍可能是私有结构，需要知道字段位置、长度、字节序、单位、版本和校验规则，不能把一个看起来合理的数字直接认作心率。

还要区分两种加密位置：

- **蓝牙链路层加密**保护无线链路。对常规连接的数据路径，控制器负责发送时加密、接收时解密，HCI 位于其主机一侧，因此本机日志仍可能看到未经过链路层加密的负载。这不表示空中传输没有加密，也不是抓包工具破解了链路密钥。
- **应用层额外加密**发生在业务负载进入蓝牙协议栈之前。这样的密文仍可能原样出现在 HCI 中；仅有 snoop 日志，并不会自动得到应用层明文。蓝牙链路加密和应用层加密可以同时存在。

控制器的链路安全职责见 [Bluetooth Core 架构与安全说明](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-60/out/en/architecture,-change-history,-and-conventions/architecture.html)。未知编码、分片缺失或中途接入造成的状态不足，也会阻止业务解析。能解析某种消息，并不等于知道整个协议，更不能证明所有数据都已采全。

## 心率为什么会出现在 8872，而不是 App 主动提供接口

在[运动心率采集案例](../android-wearable-heart-rate/README.md)中，已记录的事实是：测试手机上监听该端口的是蓝牙进程，接收器能从流中的目标业务消息解析出运动记录。这不支持“配套 App 主动向 8872 发布心率”的说法。

数据关系可以简化为：

```text
可穿戴设备发送业务数据
  → 手机蓝牙控制器 → HCI → 蓝牙协议栈 → 配套 App
                       ↓ 系统调试机制记录经过的包
                 btsnoop 日志 → 已启用的 8872 出口
                                      ↓
                              接收器重组并解析心率
```

系统日志组件处理的是 HCI 包，不需要先理解其中哪个字段是心率。被核查的 AOSP `SnoopLogger::Capture()` 接收 HCI 包，并在相应记录分支、socket 可用时把记录头和包数据写入 socket；业务 App 不需要专门实现“把心率发送到 8872”的代码。[AOSP 包记录与 socket 输出实现](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/745ee92b87ed62b5a8a1bac47d5df8cad623bf59/system/gd/hal/snoop_logger.cc#1188)

因此，应区分三个责任：设备与 App 的开发者设计业务通信，系统蓝牙实现提供调试出口，接收器开发者编写解析逻辑。仅凭在日志中看到了心率，不能推断 App 开发者故意开放数据接口、知道该手机的日志配置，或打算让第三方读取。该端口也不是配套 App 承诺维护的心率 API。

## btsnoop 是格式，文件与 TCP 是承载方式

btsnoop 使用二进制头部和逐条记录保存包、方向相关标志及时间戳。被核查的 AOSP 实现发送 16 字节文件头，标识为 `btsnoop\0`，版本为 1，链路类型为 HCI UART/H4（1002）。这些字段需要按格式解码，不能把 socket 收到的内容当作文本行。[AOSP 文件头定义](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/745ee92b87ed62b5a8a1bac47d5df8cad623bf59/system/gd/hal/snoop_logger_common.h)

| 读取路径 | 适用情况 | 边界 |
|---|---|---|
| 日志文件 | 系统已写入可提取的完整日志，需要离线分析 | 文件存在不代表普通应用或 shell 有权直接读 |
| 系统诊断包 | 用户同意导出用于排障，系统提供相关内容 | 可能只有有限内存记录；包含其他系统信息，不适合默认持续采集 |
| btsnoop TCP | 蓝牙栈已启用流式出口，需要实时分析 | 不保证端口存在，也不保证完整性或断线后的历史补发 |

官方说明中，很多设备把文件写入 `data/misc/bluetooth/logs`。启用开发者选项中的 HCI snoop 后需要重启蓝牙才能生效；常驻内存记录出于隐私考虑可能只包含非个人信息和事件。文件路径、诊断包内容和可读取范围仍需在目标系统确认。[日志采集与 btsnooz 提取说明](https://source.android.com/docs/core/connect/bluetooth/verifying_debugging)

## 8872 有 AOSP 来源，但不是跨机型保证

历史 `btsnoop_net` 文档描述了本地 TCP 端口 8872，同时要求启用 HCI 日志、将实现中的 `BT_NET_DEBUG` 编译开关设为真并重启蓝牙栈。这是该历史实现的条件，不能当成所有 Android 版本的设置步骤；普通应用无法通过勾选开发者选项修改编译开关。[历史实现说明](https://android.googlesource.com/platform/system/bt/+/ea7ab70a711e642653dd5922b83aa04a53af9e0e/doc/btsnoop_net.md)

2026-11-02 核查的 AOSP Bluetooth 提交为 `745ee92b87ed62b5a8a1bac47d5df8cad623bf59`。在这个源码快照中：

- `SnoopLoggerSocket` 默认地址为 `127.0.0.1`，默认端口为 `8872`。
- `SnoopLogger::Start()` 在日志模式不是 disabled 或 kernel 的分支中，进一步检查系统属性 `ro.debuggable`，才尝试启动 socket 线程。
- 代码注释明确指出，在 user 构建启用该 socket 实现需要通过安全审查。

这是静态源码证据，不是真机兼容性测试。打开“开发者选项”、启用“USB 调试”或给某个 APK 设置 `debuggable`，都不等于系统属性 `ro.debuggable` 为真。厂商固件或其他版本可能采用不同分支；不能从这个快照推导所有新手机都不可用，也不能从旧手机成功推导所有手机都可用。[默认地址与端口](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/745ee92b87ed62b5a8a1bac47d5df8cad623bf59/system/gd/hal/snoop_logger_socket.h)、[日志服务启动条件](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/745ee92b87ed62b5a8a1bac47d5df8cad623bf59/system/gd/hal/snoop_logger.cc#1327)

## Shizuku 不是协议依赖

TCP 服务端由蓝牙栈提供，接收端只需要按实现允许的方式建立连接并解析记录。可用的执行路径可能是普通应用、ADB 侧转发，或以 shell 身份运行的辅助进程；每条路径的权限必须分别验证。

在手机上运行接收进程时，`127.0.0.1` 指手机自己。在电脑上运行时，同一个地址指电脑自己。若手机已开放该服务，电脑已通过用户授权连接 ADB，且 Linux 主机安装了 `nc` 和 `btmon`，历史 AOSP 文档给出的调试方式是：

```bash
adb forward tcp:8872 tcp:8872
nc localhost 8872 | btmon -P -r /dev/stdin
```

第一行建立电脑到手机的转发，不会在手机上创建缺失的 btsnoop 服务。调试完成后停止接收，并用 `adb forward --remove tcp:8872` 清理本次转发。不要将抓取结果默认公开或长期保存。[AOSP 转发示例](https://android.googlesource.com/platform/system/bt/+/ea7ab70a711e642653dd5922b83aa04a53af9e0e/doc/btsnoop_net.md)

Shizuku 可以管理获授权的 shell 辅助进程，但不会让不存在的端口出现。普通应用 UID 是否能直接连接，不能仅根据地址是 loopback 推断；反过来，shell 读取成功也不能证明必须使用 Shizuku。详见 [Shizuku 的工作原理与权限边界](../android-shizuku/README.md)。

## 按层验证，不把建连成功当成采集成功

```text
系统产生所需 HCI 日志
  → 提供 TCP 出口
  → 当前进程能连接和读取
  → 文件头与后续记录有效
  → 目标负载未被过滤或截断
  → 协议状态足够、重组与字段校验通过
  → 得到目标业务记录
```

| 观察结果 | 可以说明什么 | 不能直接说明什么 |
|---|---|---|
| 连接被拒绝 | 当前端点没有接受该连接，需检查监听和启动状态 | 不等于手机完全没有 HCI 日志 |
| 权限拒绝或超时 | 需要检查执行身份、访问策略及服务状态 | 不能一律归因于 Shizuku 未授权 |
| 只收到有效文件头 | 已读到兼容格式的开头 | 不证明后续有目标包或完整记录 |
| 收到记录但没有业务输出 | 日志层有数据，应继续检查过滤、通道状态和协议 | 不证明设备没有上报目标数据 |
| 解出了记录 | 对这些输入，当前解析路径有效 | 不证明长期无丢包、固定采样率或全机型兼容 |

TCP 是字节流，一次 `read()` 可能只得到半个头，也可能合并多个包。接收器需要缓存未完成记录、检查长度并限制资源占用。断线重连应重新验证头部和解析状态，不能假设会自动补齐断线期间的记录。被核查的 AOSP socket 实现在新客户端连接时发送文件头；新连接也会替换旧客户端，因此不要假设能同时连接多个独立接收器。[AOSP socket 实现](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/745ee92b87ed62b5a8a1bac47d5df8cad623bf59/system/gd/hal/snoop_logger_socket.cc)

业务层还可能依赖连接建立时的通道协商。中途接入、应用层加密、未知帧格式和校验失败，都可能造成“有包但没有结果”。[运动心率采集案例](../android-wearable-heart-rate/README.md)保留了通道恢复方法及其录制对照，不把这种恢复策略当作所有协议的通用解析方法。

## 采集范围与隐私

HCI 日志可能包含本机多个蓝牙连接的数据，并不天然只属于当前调试的应用。只在用户明确同意的设备和会话中采集，限制接收时间和总量，只保留必要的解析结果。缺少 TCP 出口时，可以另行征得同意后使用系统支持的文件或诊断包路径，不应静默退回完整诊断包采集，也不应把改系统安全策略当作通用排障步骤。

调试结束后停止接收，移除临时转发，并按需要关闭 HCI 日志。公开示例只能使用清楚标注的合成数据，不能用合成输入证明真机表现；原始日志、设备标识和个人健康数据不应随文章发布。
