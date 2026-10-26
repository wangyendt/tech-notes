---
title: 工程笔记
description: Ye Wang 的技术笔记，记录相机与 IMU 标定、Android 和传感器数据采集。
hide: [toc, navigation]
---

# 工程笔记

记录相机与 IMU 标定、Android 开发和传感器数据采集。这里有按章节阅读的书，也有围绕具体问题写的工程笔记。

<section class="book-entry" markdown>
<p class="entry-label">标定 · 14 章 / 3 个附录</p>

## Kalibr Cam-IMU

<p class="entry-subtitle">从公式推导到 Ceres 复现</p>

从坐标系和刚体变换开始，推导相机、陀螺仪、加速度计的残差与 Jacobian，再对照 Kalibr 源码和 Ceres 实现。

<div class="chapter-groups" markdown>

- **第 0–3 章**<br>符号、坐标系与最小二乘
- **第 4–10 章**<br>观测模型、连续时间轨迹与 Jacobian
- **第 11–13 章**<br>源码对应、初始化与多传感器
- **附录 A–C**<br>李群公式、数值验证与速查表

</div>

[阅读全文与章节目录 →](calibration/kalibr-cam-imu/README.md){ .entry-link }

<p class="entry-note">正文和配图从源项目同步，保留原稿的 draft 状态。<a href="sources/">查看来源与原始文件</a></p>
</section>

<section class="article-entry" markdown>
<p class="entry-label">系统与工程 · Android · 2026-10-26</p>

## 在 Android 上采集可穿戴设备的心率数据

保留某 App 的蓝牙连接，用无障碍控制运动开始和结束，通过本机蓝牙日志流接收心率。记录 Shizuku 的使用、控件树故障的定位，以及拔线、锁屏测试中的数据间隔。

[阅读工程笔记 →](systems/android-wearable-heart-rate/README.md){ .entry-link }
</section>

<div class="home-bottom" markdown>

[标定](calibration/README.md) · [系统与工程](systems/README.md) · [关于本站](about/README.md) · [GitHub](https://github.com/wangyendt/tech-notes)

</div>
