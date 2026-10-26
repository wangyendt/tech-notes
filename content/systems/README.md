---
title: 系统与工程
tags: [工程实践]
---
# 系统与工程

Android、设备通信和数据采集的实现笔记。

## Android

[在 Android 上采集可穿戴设备的心率数据](android-wearable-heart-rate/README.md)

保留某 App 的蓝牙连接，控制运动开始和结束，从本机蓝牙日志流保存心率。包括权限配置、控件树故障定位和数据质量统计。案例已匿名处理。


## watchOS 与 BLE

[Apple Watch：BLE Central 与后台运行配置](watchos-ble-central-background/README.md)

手表主动写入手机的 GATT 服务，包含分片协议、Xcode 权限与后台模式、会话生命周期和真机验收清单。基于匿名化工程的静态核查，不把配置声明写成已验证的保活结果。
