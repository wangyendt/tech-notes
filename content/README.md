---
title: 工程笔记
description: 从公式到代码，从现场问题到可验证结论。
---

<p class="lab-eyebrow">TECH NOTES / THEORY · IMPLEMENTATION · EVIDENCE</p>

# 把公式、代码与现场证据放在一起

这是一个按主题组织的技术知识库。长篇推导按书阅读，工程实践按问题阅读；正文只维护一份，目录、标签和阅读路线提供不同入口。

<div class="reading-map" markdown>
<div markdown>
**公式**

模型为什么这样建立？

<small>坐标系、残差方向与 Jacobian 推导。</small>
</div>
<div markdown>
**代码**

理论怎样落到实现？

<small>数据链路、状态机和可复用的最小示例。</small>
</div>
<div markdown>
**证据**

结果究竟证明了什么？

<small>真实实验、失败信号与明确的适用边界。</small>
</div>
</div>

## 从这里开始

### 标定：按一本书建立完整理解

[**Kalibr Cam-IMU：从公式推导到 Ceres 复现**](calibration/kalibr-cam-imu/README.md)

从问题、符号和坐标系出发，进入最小二乘、相机与 IMU 残差、连续时间轨迹，再回到源码对应与数值验证。包含第 0–13 章和 3 个附录；章节沿用源项目的草稿状态，不意味着所有推导已经独立复核。

→ [标定专题导航](calibration/README.md)

### 系统与工程：从一个真实约束走到闭环

[**免 root 采集可穿戴设备心率：一次 Android 工程闭环**](systems/android-wearable-heart-rate/README.md)

保留某 App 的蓝牙连接，用独立 APK 控制运动、订阅本机日志流并保存记录。重点是权限边界、分层重组、控件可靠性、错误恢复与数据质量，而不是把一次跑通写成通用保证。

→ [系统与工程专题导航](systems/README.md)

## 如何阅读这里的结论

- **实测**：明确测试对象、条件与结果，结论不越过设备和版本范围。
- **推断**：给出依据，不把候选解释写成已证实原因。
- **待验证**：保留问题和下一步实验，不补造结果。

[阅读与验证约定](about/README.md) · [书籍来源与自动同步](sources/README.md)
