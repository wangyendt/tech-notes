---
title: 系统与工程
tags: [工程实践]
---
# 系统与工程

Android、Apple 平台开发、设备通信和数据采集的实现笔记。

## Android

### 概念与适用条件

- [Android 无障碍服务：控件树、手势与操作结果确认](android-accessibility-service/README.md)：界面观察、输入能力及业务结果确认，不把点击成功当作任务完成。
- [Shizuku 的工作原理与权限边界](android-shizuku/README.md)：应用与辅助进程的身份、启动授权和生命周期，不把 shell 等同于 root。
- [Android 蓝牙 HCI 日志：文件采集与 btsnoop TCP 流](android-bluetooth-hci-btsnoop/README.md)：HCI 与 logcat 的区别、8872 出口的构建和权限条件，以及文件、诊断包和实时流的取舍。

### 工程案例

[在 Android 上采集可穿戴设备的心率数据](android-wearable-heart-rate/README.md)

组合使用上述能力，保留配套 App 的蓝牙连接，控制某 App 的运动界面，从测试手机的 HCI 日志流解析心率。保留窗口故障、通道恢复、短时锁屏证据及数据质量统计；不将本机成功扩展为通用适配保证。案例已匿名处理。


## watchOS 与 BLE

[iPhone 与 Apple Watch 不显示开发者模式时，如何开启](iphone-apple-watch-developer-mode/README.md)

从 Device Hub 发起开发配对，让隐藏入口出现，再分别完成手机和手表的重启确认。包含旧配对缓存的识别和状态检查。

[Apple Watch：BLE Central 与后台运行配置](watchos-ble-central-background/README.md)

手表主动写入手机的 GATT 服务，包含分片协议、Xcode 权限与后台模式、会话生命周期和真机验收清单。基于匿名化工程的静态核查，不把配置声明写成已验证的保活结果。
