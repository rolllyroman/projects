/**
 * Created by Administrator on 2018/3/30.
 */
var fun_not_open = function(){
    alert('功能暂未开放');
};

var ja = ja ||{};

//Class
(function(){
    var initializing = false, fnTest = /xyz/.test(function() { xyz; }) ? /\b_super\b/ : /.*/;
    //构造基类
    var Class = function() {};
    Class.extend = function(props){
        var _super = this.prototype;
        initializing = true;
        var prototype = new this();
        initializing = false;

        for (var name in props){
            //这一段是赋值到prototype中，运用三元运算符的方式很灵活
            //满足函数的条件作为函数插入到prototype中
            prototype[name] = typeof props[name] =="function" &&
            typeof _super[name] == "function" && fnTest.test(props[name]) ?
                (function(name, fn) {
                    return function(){
                        var tmp = this._super;
                        this._super = _super[name];
                        var ret = fn.apply(this, arguments);
                        this._super = tmp;
                        return ret;
                    };
                })(name, props[name]) :
                props[name]
        }

        function Class(){
            if(!initializing && this.ctor)
                this.ctor.apply(this, arguments);
        }

        //子类prototype指向父类的实例，继承的关键
        Class.prototype = prototype ;
        Class.prototype.constructor = Class;
        //子类自动获得extend方法，arguments.callee 指向当前正在执行的函数
        Class.extend = arguments.callee;
        return Class;
    };

    ja.Class = Class;
})();

//网络
(function(){
    var Net = ja.Class.extend({
        errFunc:{
            "100":function(){
                alert('请重新登录！');
            }
        },
        ctor : function(option){
            this.options = option;
            this.success = option['success'];
            this.error = option['error'];

            var showProgress = option['showProgress'];
            if(showProgress){
                var progress = ja.Progress.init();
                this.hook('ajax', 'before', progress.update.bind(progress, 0, 3));
                this.hook('onComplete', 'before', progress.closeDelay.bind(progress));
                this.hook('onError', 'before', progress.update.bind(progress, 2, 3, 'danger'));
                this.hook('onSuccess', 'before', function(res){
                    if(res['code'] == 0){
                        progress.update(2, 3, 'success');
                    }else{
                        progress.update(2, 3, 'warning');
                    }
                });
            }
        },

        ajax: function(){
            var obj = {
                success: this.onSuccess.bind(this),
                error: this.onError.bind(this),
                complete: this.onComplete.bind(this),
            };
            var option = $.extend(this.options, obj);
            $.ajax(option);
        },

        render: function(res){
            if(res['jumpUrl']){
                window.open(res['jumpUrl']);
            }
        },

        onComplete: function(){
        },

        onSuccess: function(res){
            if(res){
                var code = res['code'];
                var success = code == '0';
                if(this.success){
                    this.success(success, res);
                }else{
                    if(success){
                        this.render(res);
                    }else{
                        this.checkCode(res);
                    }
                }
            }
        },

        onError: function(res){
            if(this.error){
                this.error(res);
            }else{
                alert(res.msg||'请求失败请重试');
            }
        },

        checkCode: function(res){
            var code = res['code'];
            if(code){
                var method = this.errFunc[code];
                if(method){
                    method(res);
                }else{
                    this.onError(res);
                }
            }
        },

        // 钩子函数
        // @params: method : ['before'/'after']
        // @example: this.hook('ajax', 'before', function(){})
        hook: function(funName, method, hookFunc){
            var hookListen = this._hookListen = this._hookListen || {};
            var _fun = Net.prototype[funName];

            if(_fun){
                var listener = hookListen[funName];
                if(!listener){
                    var obj = {
                        'before': null,
                        'after' : null,
                        'fun' : _fun
                    };
                    listener = hookListen[funName] = obj;
                    this[funName] = function(){
                        var args = Array.prototype.slice.apply(arguments);
                        //before
                        if(listener['before'])listener['before'].apply(this, args);
                        //本体
                        listener['fun'].apply(this, args);
                        //after
                        if(listener['after'])listener['after'].apply(this, args);
                    }.bind(this)
                }
                listener[method] = hookFunc;
            }else{
                console.log('无法设置钩子函数:' + funName);
            }
        },

    });
    Net.create = function(option){
        var net = new Net(option);
        net.ajax();
        return net;
    };
    ja.Net = Net;
    ja.net= Net.create;

    var Progress = ja.Class.extend({
        COLOR_SUCCESS: 'rgb(132, 255, 249)',
        COLOR_WARN: 'rgb(255, 223, 132)',
        COLOR_DANGER: 'rgb(247, 71, 71)',
        ctor: function () {
            var con = this.con = document.createElement('div');
            con.setAttribute('style',[
                'position: fixed',
                'width: 100%',
                'height: 2px',
                'top: 0',
                'left: 0',
                'z-index: 9999',
                'overflow: hidden',

                'transition: opacity 0.5s',
                '-moz-transition: opacity 0.5s',
                '-webkit-transition: opacity 0.5s',
                '-o-transition: opacity 0.5s',
            ].join(';'));
            var bar = this.bar = document.createElement('div');
            bar.setAttribute('style',[
                'width: 0%',
                'height: 2px',
                'position: absolute',
                'top: 0',
                'left: 0',
                'background: ' + this.COLOR_SUCCESS,

                'transition: width 0.5s, background 0.5s',
                '-moz-transition: width 0.5s, background 0.5s',
                '-webkit-transition: width 0.5s, background 0.5s',
                '-o-transition: width 0.5s, background 0.5s',
            ].join(';'));

            con.appendChild(bar);
            document.body.appendChild(con);
        },
        // 修改样式
        //@params: method : ['success'/'warning'/'danger']
        setState: function(method){
            var color = {
                'success': this.COLOR_SUCCESS,
                'warning': this.COLOR_WARN,
                'danger': this.COLOR_DANGER,
            }[method];
            this.bar.style.background = color || this.COLOR_SUCCESS;
        },

        // 更新进度
        setCurrent: function(num){
            this._cur = num;
            this.update();
        },

        setLimit: function(num){
            this._lim = num;
            this.update();
        },

        update: function(cur, lim, method){
            this.con.style.opacity = '1';
            if(method != null){
                this.setState(method);
            }

            cur = this._cur = (cur == null || cur==='') ? this._cur : cur;
            lim = this._lim = lim || this._lim || 1;
            this.bar.style.width = (cur / lim) * 100 + "%";
        },

        full: function(){
            var lim = this._lim = this._lim || 1;
            this.update(lim, lim);
        },

        //元素操作
        reset: function(){
            this.setState('success');
            this.bar.style.width = "0%";
            if(this._tmid)
                clearTimeout(this._tmid);
            this._tmid = null;
        },

        hide: function(){
            this.con.style.opacity = '0';
        },

        //关闭操作

        closeDelay: function(){
            var tmid = this._tmid;
            if(tmid)
                clearTimeout(tmid);

            this.full();
            this._tmid = setTimeout(function(){
                this._tmid = null;
                this.hide();
                setTimeout(this.reset.bind(this), 500);
            }.bind(this), 500)
        },

        closeWarning: function(){
            this.setState('warning');
            this.closeDelay();
        },

        closeDanger: function(){
            this.setState('danger');
            this.closeDelay();
        }
    });
    Progress.getInstance = function(){
        var instance = Progress.shareInstance = Progress.shareInstance ? Progress.shareInstance : (Progress.shareInstance = new Progress());
        return instance;
    };
    Progress.update = function(cur, lim){
        var instance = Progress.getInstance();
        instance.reset();
        instance.update(cur, lim);
    };
    Progress.init = function(){
        ja.progress = Progress.getInstance();
        ja.progress.reset();
        return ja.progress;
    };
    ja.Progress = Progress;



})();

