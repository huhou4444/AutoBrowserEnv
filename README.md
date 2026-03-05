# AutoBrowserEnv
全自动在node中生成浏览器函数、原型继承关系

运行此脚本会自动打开浏览器将浏览器中特有的构造函数、原型对象的属性描述符、原型继承关系、Symbol属性保存下来，然后写入到./env.js文件中，并且把函数的返回值统一设置为“补”，方便后续补环境

<img width="1074" height="982" alt="image" src="https://github.com/user-attachments/assets/1d018f70-78a4-481b-9ab7-97bc9058d08e" />

可以看到生成的环境有五万多行
<img width="1042" height="739" alt="image" src="https://github.com/user-attachments/assets/a127245b-41fb-4c93-bcea-c5abb4d9cf0c" />
