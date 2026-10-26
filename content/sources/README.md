# 书籍来源与自动同步

## 唯一来源

《Kalibr Cam-IMU：从公式推导到 Ceres 复现》的正文维护在 [kalibr-camimu-ceres](https://github.com/wangyendt/kalibr-camimu-ceres)，不是在本站维护另一份。

具体的仓库、分支、书籍子目录和网站挂载位置由知识库根目录的 `books.json` 声明。每次构建都在本页追加对应的源提交和目录树；章节、图片和阅读顺序从源目录导入，draft 状态原样保留。网站上线不等于推导已经独立审查。

## 什么时候更新

- 本站原生内容推送到 `main` 时构建。
- 默认每小时检查一次源仓库声明的分支；只有书籍目录或网站内容发生变化才重新部署。
- 仓库 Actions 支持手动运行；也预留 `repository_dispatch` 的 `book-updated` 事件入口。
- 本地编辑源书不会直接更新网站，必须先把修改推送到源仓库对应分支。

定时任务可能延迟，不承诺推送后立即更新。公开仓库长期无活动时，平台也可能停用定时任务；应检查 Actions 状态。

## 为什么不双向复制

只读取声明的书籍子目录，不执行源仓库代码，不把生成副本提交回源项目或本站分支。书籍修改回源仓库，本站文章修改回本站。一处正文、多个阅读入口。

如果以后需要源仓库 push 后立即同步，可由源工作流发送跨仓库事件；这需要额外授权凭据。目前默认小时级同步不需要它，也没有修改源项目。

[源事件与定时任务说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
