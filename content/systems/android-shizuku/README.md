---
type: article
title: Shizuku 的工作原理与权限边界
description: 区分普通应用、ADB shell 和 root，理解 Shizuku 的 Binder 与辅助进程机制、启动条件及不能保证的系统能力。
tags: [Android, Shizuku, ADB, 权限]
date: 2026-11-02
updated: 2026-11-02
---

# Shizuku 的工作原理与权限边界

普通 Android 应用有时需要调用自身权限不足、但 ADB shell 可以使用的系统能力。Shizuku 提供了一个由用户启动和授权的服务，让应用通过它完成相应操作。它不是漏洞利用，也不是给所有应用授予无限权限：可执行范围取决于服务的启动身份和目标系统的访问策略。

判断一项功能是否可用，要分别确认服务正在运行、应用已经获授权、执行进程身份符合预期，以及目标资源确实允许访问。这四项不能用一个“Shizuku 已安装”状态代替。

## 应用没有整体变成 shell 或 root

Shizuku 可以转发 Binder 调用，也可以通过 UserService 在独立进程中运行应用提供的 Java 或 JNI 代码。普通应用继续使用自己的 UID；需要不同身份的操作交给服务或辅助进程，再通过进程间通信返回结果。[Shizuku 原理介绍](https://shizuku.rikka.app/introduction/)

```text
普通应用：界面、用户确认、结果保存
  ↓ 用户授予 Shizuku 访问权限后，通过 Binder 通信
Shizuku 服务 / UserService 辅助进程
  ↓ 使用该进程的 UID、权限及 SELinux 上下文
目标系统接口、文件或 socket
```

| 启动方式 | 常见执行身份 | 不能据此推导的能力 |
|---|---|---|
| ADB 启动，包括无线调试 | shell，UID 2000 | 不等于 root，不保证能读其他应用私有数据或任意日志文件 |
| 已有 root 的设备上启动 | root，UID 0 | Shizuku 不负责让设备获得 root，访问仍受系统安全策略约束 |

Shizuku 的开发指南说明了两种身份的差异，并提供 `Shizuku.getUid()` 查询服务身份；在辅助进程中还应核对其实际身份。不要只根据启动按钮或“授权成功”猜测当前权限。[Shizuku API 开发指南](https://github.com/RikkaApps/Shizuku-API)

Android 的权限检查不仅涉及 UID。系统服务的权限校验、文件访问权限、Linux capabilities 和 SELinux 都可能影响结果；SELinux 的强制访问控制也适用于 root 进程。[Android SELinux 说明](https://source.android.com/docs/security/features/selinux)

## 启动、授权和连接是不同状态

非 root 使用时，用户需要先启用相应调试能力并启动服务。Android 11 及以上支持通过无线调试在设备上配对和启动；也可以按官方流程连接电脑启动。非 root 模式下重启手机后需要重新启动服务，不能把曾经成功配对理解为服务永远在线。[Shizuku 设置手册](https://shizuku.rikka.app/zh-hans/guide/setup/)

应用还需要单独请求 Shizuku 授权。无线调试配对表示建立了调试信任关系，Shizuku 应用授权表示允许该应用使用服务，两者不是同一个许可。

可以按以下顺序显示状态并处理故障：

1. **服务未连接**：提示用户检查启动状态，不先尝试受限操作。
2. **应用未授权**：解释需要的具体能力，让用户决定是否授权。
3. **执行身份不符合要求**：报告当前模式，不把 shell 模式当作 root 模式使用。
4. **资源不可访问**：区分权限拒绝、接口不存在和服务端未启动。
5. **运行中断开**：关闭接收器、取消未提交操作，保留错误，等待重新连接。

UserService 并不是普通 Android 应用进程，不能假设其 `Context` 支持常规应用中的全部 API。把读取任务放进去，也不等于获得后台长期保活保证。接口应限定到需要的操作和数据，不向外暴露任意命令执行入口。[UserService 的能力与限制](https://github.com/RikkaApps/Shizuku-API#userservice)

## 为什么有 Shizuku 仍可能读不到 8872

`127.0.0.1:8872` 的服务端来自某些 Android 蓝牙栈实现，不来自 Shizuku。Shizuku 可以为接收代码提供一种执行身份，但不能替系统创建原本没有启用的 btsnoop 出口。

| 条件 | Shizuku 能否代替它 |
|---|---|
| 蓝牙栈包含并启动 TCP 日志服务 | 不能；需要匹配的系统实现和配置 |
| 当前进程允许连接该 socket | 可能因执行身份而不同，必须实测，不能承诺 shell 一定成功 |
| 日志包含目标业务负载 | 不能；过滤、截断、采集时机影响内容 |
| 解析器能理解目标协议 | 不能；协议重组和字段解析是另一层工作 |

普通应用 UID 若能直接读取，就不必仅为这个 socket 引入 Shizuku。若只有 shell 路径验证成功，Shizuku 是可选的进程管理和授权方式之一，不是 btsnoop 协议要求。通过电脑 ADB 转发能读到，也不能证明普通应用 UID 在手机内直接读取同样可行。

具体启动条件、日志与 logcat 的区别，以及逐层验证方法见 [Android 蓝牙 HCI 日志：文件采集与 btsnoop TCP 流](../android-bluetooth-hci-btsnoop/README.md)。

## 案例证据与权限最小化

[运动心率采集案例](../android-wearable-heart-rate/README.md)使用非 root、ADB 启动方式，并要求辅助进程以 shell UID 运行。该案例验证了测试手机上的接收路径，没有单独验证普通应用 UID 的直接访问，也没有证明其他手机必须或只需安装 Shizuku 就能采集。

设计新功能时，优先使用已有的普通应用 API，只把确实需要不同权限的任务交给辅助进程。为读取设置超时和大小限制，只返回目标结果，不默认导出完整日志。无障碍服务需要独立授权，其界面操作能力见[无障碍服务概念文章](../android-accessibility-service/README.md)。
