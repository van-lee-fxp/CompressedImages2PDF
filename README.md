# 图片压缩包转 PDF 转换工具

## 背景

在阅读漫画时，有的时候从网络上下载到的漫画资源为打包成压缩包的图片文件，特别不方便阅读，因此会希望将这种以压缩包形式存储的图片文件转化为方便阅读的 PDF 文件。为了实现这一目的，我使用 Python 编写了这样的一个简易小工具，来实现图片压缩包到 PDF 文件的批量转换。

## 程序的运行

此工具需要使用到的外部包如下——

* `pathlib` ——用于实现方便的文件路径定位
* `rarfile`, `py7zr` ——提供对 `.rar`, `.7z` 格式压缩包的支持
* `gooey` ——用于给程序生成图形界面，方便操作
* `img2pdf` ——用于将多张图片合成为 PDF 文件
* `pyrsistent` ——用于创建不可变映射 (字典)
* `pillow` ——用于图片格式的识别和图片的处理

将程序源代码下载到本地后，先确保这些包已经安装，然后可直接运行主程序 `__main__.py`, 设定好输入文件夹和输出文件夹。输入文件夹为图片压缩包的存放位置，程序会遍历输入文件夹下的所有文件并找出压缩包。当输出文件夹为空的时候，程序会直接将转换好的 PDF 放置在输出文件夹中，否则程序会建立一个名为 `out` 的文件夹作为实际输出目录，以防出现文件重名被覆盖的情况。

### 细节设定与异常处理

以下为程序运行时可供选择的选项及其含义——

* **忽略压缩包中的非图片文件** (Skip Non-Image Files): 若压缩包中存在非图片文件，默认情况下，这些非图片文件会被直接存放到输出目录。若启用该选项，则直接忽略非图片文件
* **当 PDF 转换失败时，自动清除解压的文件** (Remove Extracted Files for Failed PDF Conversions): 若图片转换为 PDF 的过程出错，默认情况下，会将解压的文件存放在一个名为 `<原压缩文件名>_extracted` 的文件夹内并保留。若启用此选项，则解压的文件会被自动删除
* **忽略解压失败的压缩包** (Ignore Compressed Files if Extraction Fails): 若压缩包解压失败 (如需要密码)，默认情况下，压缩包会被直接复制到输出目录。若启用此选项，则不复制解压失败的压缩包
* **在输出文件夹中使用扁平目录结构** (Flattened Directory Structure): 默认情况下，若输入文件夹内有深层目录树，则输出文件夹中会保留和输入文件夹相同的目录结构。启用此选项时，会将生成的 PDF 文件直接保存在输出目录文件夹下，而不保留原有的目录树
* (⚠️ 谨慎启用此项) **自动覆盖重名文件** (Auto-Replace Existing Files): 默认情况下程序会采用后加括号数字的方式来避免文件或文件夹名称冲突，防止意外的文件覆盖。启用此项后，重名文件会被直接覆盖。**请务必谨慎启用此项！！！**

## 已知问题

* 目前只支持 `zip`, `rar`, `7z`, `tar` 这 4 种压缩包格式
* 程序还未实现当压缩包有密码的时候，自动使用输入的密码解压 (需要保证密码已知且所有文件拥有相同的密码) 的功能
* 尚不支持自定义图片排序方法 (大部分情况下，压缩包里的图片是按照前面补 0 的正整数来命名的，这样子排序就不会出错。但如果序号前面没有补 0, 就有可能出现 10, 11 排在 1 前面这样的错序)
* 尚不支持自定义输出 PDF 文件的名称。目前采用的是和原压缩包相同的名称