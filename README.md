# 工程笔记 · Tech Notes

按主题组织的技术知识库：一篇文章、一本书或一个专题一个文件夹，一份正文，多个入口。

**在线阅读：<https://wangyendt.github.io/tech-notes/>**

## 内容

- [标定专题](content/calibration/README.md)：《Kalibr Cam-IMU：从公式推导到 Ceres 复现》，第 0–13 章与 3 个附录。正文唯一来源为 [kalibr-camimu-ceres](https://github.com/wangyendt/kalibr-camimu-ceres/tree/master/docs/books/kalibr_cam_imu_from_equations_to_ceres)。本站构建时导入，不维护手动副本。
- [系统与工程](content/systems/README.md)：[在 Android 上采集可穿戴设备的心率数据](content/systems/android-wearable-heart-rate/README.md)。应用与设备匿名；不包含个人心率明细或原始诊断包。
- [Watch BLE 与后台运行](content/systems/watchos-ble-central-background/README.md)：Central / Peripheral 连接、数据格式、Xcode 配置及真机验证方法。
- [阅读与验证约定](content/about/README.md)。

## 目录

```text
content/                   # 本站原生正文，按主题组织
  calibration/README.md    # 标定专题导航
  systems/                # 工程实践，单篇文章各占一个文件夹
books.json                 # 外部书籍的仓库、分支、源路径、挂载位置
mkdocs.yml                 # 网站导航、搜索、公式及主题配置
scripts/build_site.py      # 单向导入书籍、校验、生成导航并构建
requirements.lock          # Python 3.12 构建依赖及哈希
vendor.lock.json           # 本地托管 MathJax 资源的固定版本与完整性
.github/workflows/         # CI 与 Pages 发布
AGENTS.md                  # AI 与人工共同遵守的整理规范
```

## 网站引擎

采用 Zensical，保留兼容的 `mkdocs.yml` 配置与 Markdown 内容结构。Material for MkDocs 官方已公告于 2027-05-05 结束维护，因此新站点直接采用其维护中的后继项目。公式静态资源随站点托管。页面使用无衬线字体、浅色导航和可切换的深色阅读模式。

[迁移与兼容说明](https://zensical.org/docs/compatibility/mkdocs/migration/)

## 本地构建

需要 Python 3.12，推荐使用隔离环境。以下命令在本仓库根目录执行：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/build_site.py
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory site
```

首次构建会只读拉取源书籍目录并下载已锁定校验值的 MathJax 静态资源，需联网；不执行源项目代码。网站公式脚本和字体随站点托管，不依赖读者浏览器连接外部公式 CDN。

也可从干净的本地源项目预览：

```bash
.venv/bin/python scripts/build_site.py --book-checkout PATH_TO_KALIBR_REPOSITORY
```

书籍导入不改写正文与公式，只适配网页入口和相对链接；每次构建提供完整原始 ZIP 和 SHA-256 文件清单，包含书籍目录内全部 Git 跟踪文件。来源提示由 `overrides/main.html` 放在章节正文之后。

原生文章在 `content/` 中修改。书籍修改回源项目，提交并推送至 `books.json` 指定分支。`.cache/`、`site/` 和虚拟环境均不提交。

## 新增内容与首页收录

首页显示按主题分组的标题、类型、创建日期和更新日期，不维护摘要或章节数。构建时从正文元数据生成，不需要手改首页条目。

原创文章放到 `content/主题/文章目录/README.md`，在文件顶部添加：

```yaml
---
type: article
title: 文章标题
date: 2026-10-26
updated: 2026-10-26
---
```

本仓库维护的多章书籍入口使用 `type: book`。标题优先读取 front matter 的 `title`，未填时读取首个一级标题。分组取顶层主题目录，分组名称取该目录的 `README.md`；同组按更新日期降序，更新日期相同时按创建日期降序，再按标题排序。未填写日期的条目排在最后。专题介绍、关于页和没有 `type` 的章节不会被当作单独文章收录。

日期使用 `YYYY-MM-DD`。`date` 表示内容创建日期；内容修订时维护 `updated`，未填写 `updated` 时默认采用 `date`。两者都缺失时显示“未填写”，不采用当前时间或部署时间补造日期。仅修改主题或重新部署不会刷新内容日期。

外部书籍优先使用源 README 的日期元数据；缺少时，以源目录在完整 Git 历史中的首次记录和最近变更作为可追溯日期。这不等于作者真正开始写作的时间。构建只检出书籍子目录，但为日期计算读取完整提交历史；来源页提供对应提交链接。日期随源目录变更自动更新，源项目其他文件变动不改变书籍更新时间。

当前外部 Kalibr 书籍由 `books.json` 登记来源，首页标题直接读取本次导入的源书 README，不修改源书补元数据。现有导入器仍是单一外部书籍源；新增本地书籍可直接收录，新增其他外部书籍需扩展导入配置与同步流程。

首页自动收录不等于自动重写专题正文或网站侧栏导航；若新增文章需要进入侧栏，仍需在 `mkdocs.yml` 登记。原有文章改标题后，首页会随构建自动更新。

## 自动同步

1. 本仓库 `main` 推送时构建与发布。
2. 默认每小时第 17 分钟检查源仓库 `master`（UTC 时区）；书籍目录树或本站内容指纹变化时重建。
3. Actions 支持手动运行；`force=true` 可强制重建。
4. 预留 `repository_dispatch: book-updated`，但当前不依赖源仓库回调，也未要求额外跨仓库密钥。

**本地文件修改不等于远端更新。** 必须推送源项目，网站才能读取。GitHub 定时任务可能延迟，公开仓库长期无活动时也可能被平台停用，因此不承诺实时同步；需要即时更新时可手动运行。每次网站构建公开来源提交与书籍目录树，便于追溯。[事件文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

若导入、校验或严格构建失败，不执行新部署，保留此前已上线版本。源项目目前为公开仓库，默认同步无需额外令牌。

## 配置评论、点赞与浏览量

互动区由网站模板统一添加到原生文章、本地书籍入口和导入书籍的阅读页；首页、专题目录、关于页和书籍素材说明不显示。源书正文不变。浏览量位于标题下，评论和 👍 反应及其数量位于正文与来源提示之后。单页可在 front matter 设置 `comments: false` 关闭整个互动区。

不蒜子由 `mkdocs.yml` 的 `extra.engagement.pageviews` 控制。本站已配置 Giscus 的 Announcements 分类，两个服务均启用。迁移仓库或重新配置时按以下步骤操作：

1. 在 [仓库设置](https://github.com/wangyendt/tech-notes/settings) 的 Features 中开启 Discussions。
2. [安装 Giscus GitHub App](https://github.com/apps/giscus)，仅授权 `wangyendt/tech-notes`。
3. 在 Discussions 中选择或创建 Announcements（公告类型）分类；访问 [Giscus 配置页](https://giscus.app/zh-CN)，输入 `wangyendt/tech-notes` 并选择该分类。
4. 将生成配置中的 `data-repo-id`、`data-category`、`data-category-id` 填入 `mkdocs.yml` 的 `extra.engagement.giscus` 对应字段，再设置 `enabled: true`。这些是公开 ID，不是密钥；不要填写 GitHub Token。仓库与分类 ID 已经核对；更换分类时应重新获取 ID。
5. 运行单元测试、前端回归测试和严格构建，然后将修改提交、推送到 `main`，由现有 GitHub Pages 工作流发布：

   ```bash
   .venv/bin/python -m unittest discover -s tests -v
   node --test tests/engagement.test.cjs
   .venv/bin/python scripts/build_site.py
   ```

只需要从配置页复制仓库与分类字段，不要把整段脚本重复粘贴进正文。本站固定使用 canonical URL 的 pathname 作为 `specific` 映射字符串，开启严格匹配、中文界面、主帖反应和深浅主题同步。例如 `/tech-notes/systems/watchos-ble-central-background/`；修改文章标题不影响对应讨论，但变更路径需要迁移讨论标题及严格匹配哈希。首次有人评论或回应时，Giscus 才会创建对应讨论。

`giscus.json` 将嵌入来源限制为 `https://wangyendt.github.io`；这是域名级限制，不隔离该域名下的其他项目路径。若将来更换域名，需要一起更新 `site_url` 和该白名单。本地及其他域名预览不加载这两个服务，避免测试浏览计数或产生测试讨论。带查询参数或非 canonical 路径的页面不加载不蒜子，避免泄漏授权参数或拆分计数。当前使用完整页面导航；若将来启用 instant navigation，应先补充组件卸载、重新初始化和跨页计数测试。

发布后检查两篇文章和两个书籍章节的浏览量分别加载、评论不串页、深浅主题切换及手机宽度。登录后由维护者手动验证一次评论和 👍 反应，再删除测试评论、取消反应。刷新会产生新的页面访问，数字不是独立人数，也不能补算历史阅读。服务受阻或超时时显示不可用提示，不阻塞正文；无法保证防刷或第三方服务可用性。

停用时将 `pageviews` 和 `giscus.enabled` 改为 `false` 后重新发布，不会删除 GitHub 中的历史讨论。[读者可见的数据说明](content/about/README.md#interaction-privacy)。

## 内容权利与隐私

原生正文与导入书籍保留各自作者及来源，不因汇编在此而改变原有权利。源书籍仍按原文 draft 状态呈现。第三方前端资源保留自身许可证；本站未为所有内容统一另授开源许可证。

工程案例仅公开必要的技术结构和聚合结果；不要上传 APK、密钥、设备标识、个人健康明细或原始系统诊断。
