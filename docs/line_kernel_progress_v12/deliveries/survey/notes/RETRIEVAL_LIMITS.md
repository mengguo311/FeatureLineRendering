# 取得范围与引用限制

本文件是研究者的检索记录，不是论文原文。原句证据仅来自 `evidence/` 保存的真实网页工具输出、下载的作者项目HTML和PDF文字抽取。`SOURCE_READING_REGISTER.json` 区分具体阅读范围；引文编号全部由提供的 `sources.py add` 返回。

- 已取得并阅读相关方法章节：Lifted Multicut 2015（arXiv v2）、PEARL（作者IJCV版）、Zhang等费用流关联（原论文的学术镜像）、LIMAP（arXiv v1）、L1-medial（作者PDF）。PDF和pdftotext文字均保存；没有安装工具。
- 经web取得全文并阅读相关部分：Lifted Multicut约束研究2017、T-Linkage扩展论文2017、Principal Curves。保存的是网页工具实际返回的相关页段，不宣称本地有整篇PDF。T-Linkage本地下载超过本次8MiB单文件限额而未保存，网页相关节已读；另读作者2014会议版本的引言和方法概述。
- StrokeAggregator、StrokeStrip：只阅读作者项目页的方法说明及代码入口。StrokeStrip另读作者README的输入格式，明确需已有cluster_id，并核实Gurobi许可依赖。没有阅读其28MB全文；未将项目页当成全文。StrokeAggregator页面提供Windows binary及非商业使用说明，未验证二进制兼容性。
- NEF：作者项目页/摘要和代码入口已读；搜索返回过方法段落，但不将搜索摘要或片段冒称完整论文阅读。它只用于条件路线对比，不作为Top3迁移的核心依据。
- CVF的PEARL/Multicut相关PDF存在web大小限制，LIMAP/NEF页面存在403；PEARL、Multicut、LIMAP后来通过公开作者/arXiv文件取得。保留初次失败工具输出，没有将失败状态改写为成功。
- 本次未核实PEARL完整端到端实现、原始tracking作者程序、Principal Curves/L1-medial当前可下载实现；报告明确UNVERIFIED。作者声明或第三方实现不等于本机可运行。LIMAP当前repo已演进，不等同于2023论文版本。
- `code_availability.txt` 等文件包含页面导航和检索噪声；只使用所读原文/作者材料支持正文，不将第三方摘要作为核心证据。
- `sources.py quote` 首次为两个代码入口录入过不足三个词的短句，工具真实拒绝；随后从原页面选用合格原句重录，实际回执在 `CITATION_REPAIR_RECEIPTS.json`。没有伪造PASS。
- CLI `verify --evidence` 的中文句子统计为0。真实返回0和“citations OK”仅表示编号、Sources与原句证据链成立，不代表所有断言逐句核验，更不代表方案有效。

全文材料仅作本次个人研究参考；研究报告以概括和简短原句账本为主。没有根据引用数量、代码存在或优化最优性推断本资产的视觉收益。
