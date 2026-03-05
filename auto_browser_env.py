
from DrissionPage import Chromium
browser = Chromium()
tab = browser.latest_tab
tab.get('https://www.baidu.com')


def find_all_constructor():
    """
    获取浏览器上有，但是node没有的构造函数
    :return:
    """
    script = r"""
        (function() {
    const constructors = [];
    const props = Object.getOwnPropertyNames(window);
    props.forEach(prop => {
        try {
            const val = window[prop];     
            if (typeof val !== 'function') return;
                const protoName = val.prototype && Object.prototype.toString.call(val.prototype);
                constructors.push(prop);
        } catch (e) {}
    });
    return constructors;
})();
    """
    js_r = tab.run_js_loaded(script, as_expr=True)
    result = []
    for _i in js_r:
        node_type = execjs.eval(f'typeof {_i}')
        print('正在检查', _i, '在node中是否存在', node_type)
        if node_type == 'undefined' or _i == 'EventTarget':
            result.append(_i)
    return result

def proto_script(constructor_name):
    script = r"""
        (()=>{
            if(typeof %s != 'undefined'){
                return Object.prototype.toString.apply(%s.prototype.__proto__).split(' ')[1].replace(']', '')
            }
        })()
        """ % (constructor_name, constructor_name)
    j_result = tab.run_js_loaded(script, as_expr=True)
    if j_result == 'WindowProperties':
        j_result = 'EventTarget'
    result = f'{constructor_name}.prototype.__proto__ = {j_result}.prototype'
    return result


def desc_script(constructor_name):
    script = r"""
        (()=>{
            function toJsonStrReplace(key, value) {
                if (typeof value === "function") {
                    let funcName = ''
                    if (value.name.indexOf(' ') !== -1) {
                        funcName = value.name.split(' ')[1]
                    } else {
                        funcName = value.name
                    }
                    if(['delete','default','continue','finally', 'catch'].includes(funcName)){
                        funcName = ''
                    }
                    if (key === 'get' || key === 'set') {
                        //属性
                        if (key === 'get') {
                            return `function ${funcName}(){return '补'}`
                        }
                        if (key === 'set') {
                            return `function ${funcName}(){return '补'}`
                        }
                    }
                    if (key === 'value') {
                        //函数
                        return `function ${funcName}(){return '补'}`
                    }
        
                } else if (value === undefined) {
                    return 'undefined'
                } else {
                    return value
                }
            }
            let propMap = Object.getOwnPropertyDescriptors(%s.prototype);
            let code = ''
            for (let prop of Reflect.ownKeys(propMap)) {
            //desc 属性描述符
            //propMap 一个map，key是属性名，value是属性描述符
            //prop 属性名
            let desc = propMap[prop];
            //属性的类型
            let type = ''
            try {
                let val = %s.prototype[prop];
                if (%s.prototype === val) {
                    //跳过自己引用自己的对象，比如self、globalThis
                    continue
                }
                type = typeof val
            } catch (e) {
            }

            if (typeof prop === 'symbol') {
                let str = prop.toString();
                str = str.replaceAll('Symbol(', '').replaceAll(')', '')
                code += `[${str}]: ${JSON.stringify(desc)},`
            } else if (prop === 'constructor') {
                code += `constructor: %s,`
            } else {
                if (type === 'function') {
                    // toStringProtectFuncName.push(`hhx.func_str(${objStr}.${prop})`)
                }
                let value = JSON.stringify(desc, toJsonStrReplace)
                value = value.replaceAll(`:"function`, `: function`)
                value = value.replaceAll(`}",`, `},`)
                value = value.replaceAll('"undefined"', 'undefined')
                value = value.replaceAll('"hhx', 'hhx')
                value = value.replaceAll(')"', ')')
                code += `${prop}: ${value},`
            }
            code += '\n'
            }
        return code})()
        """ % (constructor_name, constructor_name, constructor_name, constructor_name)
    js_r = tab.run_js_loaded(script, as_expr=True)
    result = f"""
        Object.defineProperties({constructor_name}.prototype, {{
            {js_r}
        }})
    """

    return result


def constructor_script(constructor_name):
    script = r"""
        (()=>{
            let result = ''
            try {
                eval(`new %s()`)
            } catch (e) {
                if (e.message.includes('Illegal constructor')) {
                    result += `throw new TypeError("${e.message}")`
                }
            }
            return result
        })()
        
    """ % constructor_name
    js_r = tab.run_js_loaded(script, as_expr=True)
    result = f'''
        {constructor_name} = function {constructor_name}() {{
            if (new.target){{
                {js_r}
            }}
        }}
        '''

    return result


solo_lines = []
cells = {}

all_constructor = find_all_constructor()

for constructor in all_constructor:
    exist = tab.run_js_loaded(f'typeof {constructor}', as_expr=True)
    if exist:
        if constructor not in cells:
            cells[constructor] = []
            try:
                constructor_init = constructor_script(constructor)
                cells[constructor].append(constructor_init)
                proto_exist = tab.run_js_loaded(f'typeof {constructor}.prototype', as_expr=True) != 'undefined'
                if proto_exist:
                    desc = desc_script(constructor)
                    if '-' not in desc:
                        cells[constructor].append(desc)
                    proto = proto_script(constructor)
                    cells[constructor].append(proto)


            except Exception as e:
                cause = e.__dict__['_kwargs']['INFO']['exception']['description']
                if 'is not defined' in cause:
                    continue
                raise e

    pass

def sort_cells(cells_: dict[str, list]):
    """拓扑排序，确保父原型在子原型之前定义"""
    # 构建依赖关系图：key -> 其父原型
    dependencies = {}
    for k in cells_:
        if len(cells_[k]) > 2:
            proto_line = cells_[k][2]
            # 格式: "XXX.prototype.__proto__ = YYY.prototype"
            dependencies[k] = proto_line.split(' = ')[1].removesuffix('.prototype')
        # else:
        #     print(f'未找到 {cells_[k][0]} 的原型')

    result = []
    visited = set()

    def visit(key):
        """递归访问，确保父原型先被添加"""
        if key in visited:
            return
        if key not in cells_:
            # 父原型不在 cells_ 中（可能是内置对象如 Object），跳过
            return

        # 先访问父原型
        parent = dependencies.get(key)
        if parent:
            visit(parent)

        # 再添加当前原型
        visited.add(key)
        result.append(key)

    # 对所有 key 进行拓扑排序
    for k in cells_:
        visit(k)

    return result


key_list = sort_cells(cells)

with open(r'./env.js', 'w', encoding='utf-8') as f:
    for i in key_list:
        for ii in cells[i]:
            f.write(ii + '\n')
print(f'环境已生成 当前目录下 env.js 文件')

