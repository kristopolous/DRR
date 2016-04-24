//
// EvDa Events and Data 
// See EvDa.version at the end for version info.
//
// https://github.com/kristopolous/EvDa
//
// Copyright 2008 - 2016 Chris McKenzie
// Dual licensed under the MIT or GPL Version 2 licenses.
//
var 
  module = module || {},
  EvDa = module.exports = (function (){
  'use strict';

  var 
    slice = Array.prototype.slice,  

    // This is mostly underscore functions here. But they are included to make sure that
    // they are supported here without requiring an additional library. 
    //
    // underscore {
    toString = Object.prototype.toString,
    isArray = [].isArray || function (obj) { return toString.call(obj) === '[object Array]' },
    isFunction = function (obj) { return !!(obj && obj.constructor && obj.call && obj.apply) },
    isString = function (obj) { return !!(obj === '' || (obj && obj.charCodeAt && obj.substr)) },
    isNumber = function (obj) { return toString.call(obj) === '[object Number]' },
    isScalar = function (obj) { return isString(obj) || isNumber(obj) },
    isObject = function (obj) {
      if ( isFunction(obj) || isString(obj) || isNumber(obj) || isArray(obj)) {
        return false;
      }

      return obj == null ? 
        String ( obj ) === 'object' : 
        toString.call(obj) === '[object Object]' || true ;
    },

    toArray = function (obj) {
      return slice.call(obj);
    },

    each = [].forEach ?
      function (obj, cb) {
        if ( isScalar(obj)) {
          return each([obj], cb);
        } else if ( isArray(obj) || obj.length ) { 
          toArray(obj).forEach(cb);
        } else {
          for ( var key in obj ) {
            cb(key, obj[key]);
          }
        }
      } :

      function (obj, cb) {
        if (isScalar(obj)) {
          return each([obj], cb);
        } else if (isArray(obj)) {
          for ( var i = 0, len = obj.length; i < len; i++ ) { 
            cb(obj[i], i);
          }
        } else {
          for ( var key in obj ) {
            cb(key, obj[key]);
          }
        }
      },

    last = function (obj) {
      return obj.length ? obj[obj.length - 1] : undefined;
    },

    values = function (obj) {
      var ret = [];

      for (var key in obj) {
        ret.push(obj[key]);
      }

      return ret;
    },

    keys = ({}).keys || function (obj) {
      if ( isArray(obj) ) { 
        return obj;
      }
      var ret = [];

      for ( var key in obj ) {
        ret.push(key);
      }

      return ret;
    },

    without = function (collection, item) {
      var ret = [];
      each(collection, function (which) {
        if (which !== item) {
          ret.push(which);
        }
      });
      return ret;
    },

    uniq = function (obj) {
      var 
        old, 
        ret = [];

      each(keys(obj).sort(), function (which) {
        if (which != old) {
          old = which;
          ret.push(which);
        }
      });
      return ret;
    },

    select = function (obj, test) {
      var ret = [];
      each(obj, function (which) {
        if (test(which)) { ret.push (which); }
      });
      return ret;
    },

    size = function (obj) {
      return (obj && 'length' in obj) ? obj.length : 0;
    },

    map = [].map ?
      function (array, cb) { 
        return array.map(cb) 
      } : 

      function (array, cb) {
        var ret = [];

        for ( var i = 0, len = array.length; i < len; i++ ) { 
          ret.push(cb(array[i], i));
        }

        return ret;
      },

    clone = function (obj) {
      if (isArray(obj)) { return slice.call(obj); }
      if (isObject(obj)) { return extend(obj, {}); }
      return obj;
    },

    extend = function (obj) {
      each(slice.call(arguments, 1), function (source) {
        for (var prop in source) {
          if (source[prop] !== void 0) {

            // This recursively assigns
            /*
            if ( isObject(source[prop]) && isObject(obj[prop]) ) {
              extend(obj[prop], source[prop]);
            } else {
             */ obj[prop] = source[prop];
            //}
          }
        }
      });
      return obj;
    },
    
    // } end of underscore style functions.

    isGlobbed = function (str) {
      return str.match(/[?*]/);
    },

    // This looks to see if a key has a globbing parameter, such
    // as ? or * and then return it
    glob = function (key, context) {
      if (isGlobbed(key)) {
        return select(keys(context ? context : data), function (what) {
          return what.match(key);
        });
      }
      return key;
    },

    // This uses the globbing feature and returns
    // a "smart" map which is only one element if
    // something matches, otherwise a map 
    smartMap = function (what, cback) {
      var ret = {};
      if (isArray(what)) {
        each(what, function (field) {
          ret[field] = cback(field);
        });
        return ret;

      } else {
        return cback(what);
      }
    },

    // Constants
    FIRST = 'first',
    ON = 'on',
    AFTER = 'after',
    TEST = 'test',
    OR = 'or',
    SET = "set",
    stub = function(){ return true },
    typeList = [FIRST, ON, AFTER, TEST, OR],

    // The one time callback gets a property to
    // the end of the object to notify our future-selfs
    // that we ought to remove the function.
    ONCE = {once: 1};
    
  var e = function (imported) {
    var
      lockMap = {},
      testLockMap = {},

      // Internals
      data = {},
      data_ix = {},

      // the backlog to execute if something is paused.
      backlog = [],
      globberMap = {},
      traceList = [],
      // previous values 
      logSize = 10,
      lastReturnMap = {},
      logMap = {},
      // last return
      eventMap = {},
      removedMap = {},
      dbg = {
        data: data, 
        events: eventMap,
        removed: removedMap,
        log: logMap,
        lastReturn: lastReturnMap,
        locks: lockMap,
        testLocks: testLockMap,
        trace: traceList,
        globs: globberMap
      };

    // this will try to resolve what the user
    // is asking for.
    function resolve ( what ) {
      if ( what in data ) {
        return data[ what ];
      }

      // If the key isn't set then we try to resolve it
      // through dot notation.
      // ex: a.b.c
      var 
        // [a,b,c]
        parts = what.split('.'),

        // c
        tail = parts.pop(),
        
        // a.b
        head = parts.join('.');

      if (head) {
        // we try to resolve the head
        var res = resolve( head );

        if ( isObject(res) && tail in res ) {
          return res[tail];
        }
      }
    }

    // This is the main invocation function. After
    // you declare an instance and call that instance
    // as a function, this is what gets run.
    function pub ( scope, value, meta, opts ) {
      var args = slice.call( arguments );

      if ( scope === undefined ) {
        throw "Undefined passed in as first argument.";
      }

      // If there was one argument, then this is
      // either a getter or the object style
      // invocation.
      if ( isArray(scope) ) {
        // remove the scope argument.
        args.shift();

        return map(scope, function (which) {
          return pub.apply(pub.context, [which].concat(args));
        });
      }

      // The object style invocation will return
      // handles associated with all the keys that
      // went in. There *could* be a mix and match
      // of callbacks and setters, but that would
      // be fine I guess...
      if ( isObject(scope) ) {
        if ( args.length === 1 && scope.constructor.toString().search(/{\s+\[native code\]\s+}/) === -1 ) {
          pub.context = scope;
          return;
        }
        
        var ret = {};

        //
        // Object style should be executed as a transaction
        // to avoid ordinals of the keys making a substantial
        // difference in the existence of the values.
        //
        // Also under an object style assignment passing, the
        // ordering of the arguments is naturally one off -
        // excluding the value ... this means that we cascade
        // down.
        opts = meta || {};
        meta = value;
        opts.noexec = 1;

        each( scope, function ( _key, _value ) {
          ret[_key] = pub ( _key, _value, meta, opts );
        });

        // After the callbacks has been bypassed, then we
        // run all of them a second time, this time the
        // dependency graphs from the object style transactional
        // invocation should be satisfied
        if (!opts.bypass) {
          each( ret, function ( _key, _value ) {
            if (isFunction(ret[_key]) && !isFunction(scope[_key])) {
              scope[_key] = ret[_key]();
            }
          });
        }

        // TODO: fix this
        bubble( keys(ret)[0] );

        return scope;
      }

      // This will return all the handlers associated with
      // this event.
      if ( args.length === 1 ) {
        return smartMap(scope, resolve);
      } 

      // If there were two arguments and if one of them was a function, then
      // this needs to be registered.  Otherwise, we are setting a value.
      //
      // unless it's an array of functions
      return pub [ 
        ( isFunction ( value ) || 
          ( isArray(value) && isFunction(value[0]) )
        ) ? ON : SET ].apply(this, args);
    }

    function remove_reg(key, cb) {
      if(!removedMap[key]) {
        removedMap[key] = [];
      }
      removedMap[key].push(cb || eventMap[key]);
    }

    function log(key, value, notes) {
      if (!logMap[key]) {
        logMap[key] = [];
      }

      logMap[key].push([value, new Date(), notes]);

      if (logMap[key].length > logSize) {
        logMap[key].shift();
      }
    }

    // Register callbacks for
    // test, on, after, and or.
    each ( typeList, function ( stage ) {

      // register the function
      pub[stage] = function ( key, callback, meta ) {

        // if it's an array, then we register each one
        // individually.
        if (isArray(callback)) {
          // take everything after the first two arguments
          var args = slice.call(arguments, 2);
          
          // go through the callback as an array, returning
          // its list of cbs
          return map(callback, function (cb) {
            // call within the oo binding context, the key, the cb,
            // and the remaining args.
            return pub[stage].apply(pub.context, [key, cb].concat(args));
          });
        }

        var my_map = eventMap;

        if ( !callback ) {
          return my_map[stage + key];
        }

        if ( !('ix' in callback) ) {
          extend(callback, {ref: [], ix: 0, last: false, line: []}); 
        }
        // This is the back-reference map to this callback
        // so that we can unregister it in the future.
        callback.ref.push( stage + key );

        // For debugging purposes we register where this is being registered at.
        callback.line.push ( (new Error).stack );

        if ( isGlobbed(key) ) {
          my_map = globberMap;
        }

        (my_map[stage + key] || (my_map[stage + key] = [])).push ( callback );

        //
        // It would be nice to do something like
        // ev('key', function ()).after(function (){})
        //
        // But in order for this to happen you need to proxy the first argument
        // magically over to a reference set. This isn't that hard actually 
        // and shouldn't be too expensive (lolz) anyway, a purely prototype-based 
        // approach would be awesome here but we need to do this functionally so
        // it's a bit of superfluous code where we cross our fingers and hope nobody
        // hates us.
        //
        each(typeList, function (stage) {

          if (!(stage in callback)) {
            
            callback[stage] = function (am_i_a_function) {
              // the first argument MAY be our key from above
              var args = slice.call(arguments);

              // If this is a function then we inherit our key
              if (isFunction(am_i_a_function)) {
                args = [key].concat(args);
              } 
              // However, maybe someone didn't read the documentation closely and is
              // trying to fuck with us, providing an entirely different set of keys here ...
              // that bastard.  It's ok, that's what the type-checking was all about. In this
              // case we just blindly pass everything through

              // Also we want to be clever with the return of the callbacks, since we effectively 
              // shadow the previous system. As it turns out it doesn't matter how we chain these thing
              // it just matters what temporal time we register them.  So we make the final callback 
              // an array like structure.
              if (! ('len' in callback) ) {
                // self reference
                callback[0] = callback;
                // seed it one past the self-reference minus our incrementer
                callback.len = 0;
              }
              callback.len++;
              callback[callback.len] = pub[stage].apply(pub.context, args);

              return callback;
            }
          }
        });

        return extend(callback, meta);
      }
    });

    function del ( handle ) {
      each ( handle.ref, function ( stagekey ) {
        var map = isGlobbed(stagekey) ? globberMap : eventMap;
        map[ stagekey ] = without( map[ stagekey ], handle );
        remove_reg(stagekey, handle);
      });
    }

    function isset ( key, callback, meta ) {
      // This supports the style
      // ev.isset(['key1', 'key2'], something).
      //
      // Since they all need to be set, then it doesn't really matter
      // what order we trigger things in.  We don't have to do any crazy
      // accounting, just cascading should do fine.
      if ( isArray(key) ) {
        var myKey = key.pop(), next;

        return isset(glob(myKey), function (data, meta) {
          next = (key.length === 1) ? key[0] : key;
          return isset(next, callback, meta);
        }, meta);
        // ^^ this should recurse nicely.
        // It uses the meta feature to
        // aggregate the k/v pairs as it goes through them.
        
      } 

      // This supports the style of 
      // ev.isset({
      //   key1: something,
      //   key2: something
      // })
      if ( isObject(key) ) {

        each ( key, function ( _key, _value ) {
          if (isGlobbed(_key)) {
            extend(_key, 
              smartMap(_key, function (_what){
                return isset(_key, _value, meta);
              })
            );
          } else {
            key[_key] = isset( _key, _value, meta );
          }
        });

        // Return the entire object as the result
        return key;

      } 

      var setKey = SET + key;
      // If I know how to set this key but
      // I just haven't done it yet, run through
      // that function now.
      if ( eventMap[setKey] ) {
        // If someone explicitly sets the k/v in the setter
        // that is fine, that means this function isn't run.
        //
        // NOTE: using the return value as the thing to be set is a bad idea
        // because things can be done asynchronously.  So there is no way to
        // reliably check if the code explicitly set things after the function
        // returns.
        
        // We only call this if we aren't set yet.
        if (! (key in data) ) {
          /* var ThisIsWorthless = */ eventMap[setKey](function (value) {
            pub.set.call(pub.context, key, value, meta);
          });
        }

        // register the setter if it existed.
        remove_reg(setKey);
        delete eventMap[setKey];
      }

      if ( callback ) {
        // If it already exists, then just call the function
        // that came in.
        //
        // Otherwise have it called once on a set. This means
        // that the setter is inherently asynchronous since
        // the execution of this function is continued to be
        // blocked until the key is set.
        meta = meta || {};
        return key in data ?
          callback.call ( pub.context, data[key], meta ) :
          pub[meta.first ? FIRST : ON ] ( key, callback, extend( meta , ONCE ) );
      }

      // Otherwise, if there is no callback, just return
      // whether this key is defined or not.
      return key in data;
    };

    function runCallback(callback, context, value, meta) {
      if ( ! callback.norun) {
        // our ingested meta was folded into our callback
        meta.order++;
        var res = callback.call ( 
          context, 
          value, 
          meta,
          meta.meta
        );

        if ( callback.once ) {
          del ( callback );
        }

        callback.ix++;
        callback.last = new Date();

        return res;
      }
    }

    function bubble(key) {
      var
        parts = key.split('.'),
        parts_key = parts.pop(),
        parts_obj = [];

      parts_obj[parts_key] = data[key];

      // we then extend the value into the group.
      pub.extend.apply(
        pub.context,
        [
          parts.join('.'),
          parts_obj
        ].concat(
          slice.call(arguments, 1)
        )
      );
    }

    // An internal wrapper function for the increment and decrement
    // operations.
    function mod( key, cb, arg, meta, initial ) {
      initial = initial || 0;

      var res = map(isArray(key) ? key : [key], function (which) {
        var val = isNumber(data[which]) ? data[which] : initial;
        return pub.set ( which, cb(val, arg), meta );
      });
      return isArray(key) ? res : res[0];
    }

    mod.add = function (val, amount) {
      return val + amount;
    }
        
    function test(key, _meta, _pass, _fail, _coroutine) {
      var 
        testList = eventMap[TEST + key] || [],
        testIx = 0 - 1,
        times = testList.length + 1,
        failure,
        cb = function() {
          var 
            _times = times,
            res = runCallback(
              testList[ testIx ], 
              pub.context, 
              ('_value' in meta ? meta._value : meta.value), 
              meta
            );
          // If the times value is the same then we didn't
          // recurse into the tests and instead returned
          // a truthy or falsey value, supposedly.
          if(_times == times && !!res === res) {
            meta(res);
          }
        },
        pass = function(key,meta) {
          log(key, meta.value, ['test:pass', meta]);
          return ( _pass || stub ) (key, meta);
        },
        fail = function(meta) {
          log(key, meta.value, ['test:fail', meta]);
          return ( _fail || stub ) (meta);
        },
        meta = function ( ok ) {
          failure |= (ok === false);
          times--;

          if (times < 0) { 
            return; 
          } else if ( times ) { 
            testIx++;

            if (_coroutine(meta, false)) {
              cb();
            } else {
              fail(meta);
            }
          } else if ( failure ) { 
            fail(meta);
          } else {
            pass(key, meta);
          }

          return ok;
        };

      // we should be able to do things
      // without these defined.
      _coroutine = _coroutine || stub;

      extend(meta, _meta, {
        done: meta, 
        result: meta,
      });

      return meta(true);
    }

    extend(pub, {
      // Exposing the internal variables so that
      // extensions can be made.
      _: {},
      context: this,
      list: {},
      isPaused: false,
      isok: function (key, value) {
        var res;

        test(
          key, 
          {
           _value: value,
           _isok: true
          }, 
          function pass(){ res = true; }, 
          function fail(){ res = false; }
        );

        return res;
      },

      db: data,
      debug: function (name, type) {
        if(!name) {
          return dbg;
        }

        var res = {
          lastReturn: lastReturnMap[name],
          lock: lockMap[name],
          log: logMap[name],
          value: data[name]
        };

        if (type) {
          res.events = eventMap[type + name];
          res.removed = removedMap[type + name];
        } else {
          res.events = smartMap(typeList.concat([SET]), function (type) {
            return eventMap[type + name];
          });
          res.removed = smartMap(typeList.concat([SET]), function (type) {
            return removedMap[type + name];
          });
        } 

        return res;
      },
      del: del,
      whenSet: isset,
      isset: isset,

      pause: function () {
        if (!pub.isPaused) {
          pub.isPaused = true;
          pub._.set = pub.set;
          pub.set = function () {
            backlog.push([SET, arguments]);
          }
          return true;
        }
        return false;
      }, 

      play: function () {
        if (pub.isPaused) {
          // first we take it off being paused
          pub.isPaused = false;

          // now we make a mock evda
          var mock = e();

          // unswap out our dummy functions
          pub.set = pub._.set;

          // And we run the backlog on it (with no events firing of course)
          each(backlog, function (row) {
            mock[row[0]].apply(mock, row[1]);
          });
          // clear the backlog
          backlog = [];

          // now we invoke the mock database over our own
          pub(mock.db);

          return true;
        }
        return false;
      },

      // Unlike much of the reset of the code,
      // setters have single functions.
      setter: function ( key, callback ) {
        eventMap[SET + key] = callback;

        // If I am setting a setter and
        // a function is already waiting on it,
        // then run it now.
        if ( eventMap[ON + key] ) {
          return isset ( key );
        }
      },

      when: function ( key, toTest, lambda ) {
        // when multiple things are set in an object style.
        if ( isObject(key) ) {
          var 
            cbMap = {},
            flagMap = {},
            // flagTest only gets run when
            flagReset = function (val, meta) {
              flagMap[meta.key] = false;
              meta();
            }, 
            flagTest = function (val, meta) {
              // toggle the flag
              flagMap[meta.key] = true;

              // see if there's any more false things
              // and if there are not then we run this
              if (values(flagMap).indexOf(false) === -1) {
                toTest.apply(pub.context, slice.call(arguments));
              }
            };

          each ( key, function (_key, _val) {
            // we first set up a test that will reset our flag.
            cbMap[_key + "-test" ] = pub.test(_key, flagReset);

            // then the actual test
            cbMap[_key] = pub.when(_key, _val, flagTest);

            // set the initial flagmap key
            // value to false - this will
            // be triggered if things succeed.
            // This has to be initialized here.
            flagMap[_key] = false;
          });

          return cbMap;
        }

        // See if toTest makes sense as a block of code
        // This may have some drastically unexpected side-effects.
        if ( isString(toTest) ) {
          try {
            var attempt = new Function("x", "return x" + toTest);

            // If this doesn't throw an exception,
            // we'll call it gold and then make the function
            // our test case
            attempt();

            toTest = attempt;
          } catch (ex) { }
        } else if ( arguments.length === 2 ) {
          return pub.isset ( key, toTest );
        }

        return pub(key, function (value) {
          if (
            // Look for identical arrays by comparing their string values.
            ( isArray(toTest)    && toTest.sort().join('') === value.sort().join('') ) ||

            // otherwise, Run a tester if that is defined
            ( isFunction(toTest) && toTest(value) ) ||

            // Otherwise, try a triple equals.
            ( value === toTest ) 
          ) {
            lambda.apply(pub.context, slice.call(arguments));
          }
        });
      },

      empty: function (key) {
        // we want to maintain references to the object itself
        if ( arguments.length === 0) {
          for ( var key in data) {
            delete data[key];
          }
        } else {
          each ( arguments, function (key) {
            if ( key in data) {
              if ( isArray(data[key])) {
                pub.set(key, [], {}, {bypass:1, noexec:1});
              } else {
                pub.set(key, null, {}, {bypass:1, noexec:1});
              }
            }
          });
        }
      },

      incr: function ( key, amount, meta ) {
        var 
          cb = isString(amount) ? 
            new Function("val", "return val" + amount) :
            mod.add;
        // we can't use the same trick here because if we
        // hit 0, it will auto-increment to amount
        return mod ( key, cb, amount || 1, meta );
      },

      decr: function ( key, amount, meta ) {
        amount = amount || 1;
        // if key isn't in data, it returns 0 and sets it
        // if key is in data but isn't a number, it returns NaN and sets it
        // if key is 1, then it gets reduced to 0, getting 0,
        // if key is any other number, than it gets set
        return mod ( key, mod.add, -(amount || 1), meta, 1 );
      },

      // If we are pushing and popping a non-array then
      // it's better that the browser tosses the error
      // to the user than we try to be graceful and silent
      // Therein, we don't try to handle input validation
      // and just try it anyway
      push: function ( key, value, meta ) {
        return pub.set ( key, [].concat(data[key] || [], [value]), meta );
      },

      pop: function ( key, meta ) {
        return pub.set ( key, data[key].slice(0, -1), meta );
      },

      group: function ( list ) {
        var 
          opts = toArray(arguments),
          list = opts.shift(),
          ret = pub.apply(0, opts);

        ( pub.list[list] || (pub.list[list] = []) );

        if ( isFunction(ret)) {
          pub.list[list].push(ret);
        } else {
          each(ret, function (value, key) {
            pub.list[list].push(value);
          });
        } 
        return function () {
          return pub.group.apply(0, [list].concat(toArray(arguments)));
        }
      },

      extend: function (key, value) {
        return pub.set.apply(
          pub.context, [
            key, 
            extend({}, (data[key] || {}), value)
          ].concat(
            slice.call(arguments, 2)
          )
        );
      },

      count: function (key) {
        if ( arguments.length === 0) {
          return Math.max.apply(this, values(data_ix));
        } else {
          return data_ix[key];
        }
      },

      setContext: function (what) {
        pub.context = what;
      },

      set: function (key, value, _meta, _opts) {
        _opts = _opts || {};

        var 
          bypass = _opts.bypass, 
          coroutine = _opts.coroutine || stub,
          hasvalue = ('value' in _opts),
          noexec = _opts.noexec;

        // this is when we are calling a future setter
        if ( arguments.length === 1) {
          var ret = function () {
            pub.set.apply(pub.context, [key].concat(slice.call(arguments)));
          }
          pub.set.call(pub.context, key, undefined);
          return ret;
        }

        // recursion prevention.
        if ( lockMap[key] > 0) { 
          each ( traceList, function ( callback ) {
            callback.call ( pub.context, extend({locked: key}, args) );
          });

          return data[key]; 
        }
        lockMap[key] = (lockMap[key] || 0) + 1;

        try {
          var 
            result,
            args = slice.call(arguments),

            // Tests are run sequentially, not
            // in parallel.
            doTest = (size(eventMap[ TEST + key ]) && !bypass),

            orHandler = function (_meta) {
              if(_meta) {
                meta = _meta;
              }
              // If the tests fail, then this is the alternate failure
              // path that will be run
              each ( eventMap[ OR + key ] || [], function ( callback ) {
                runCallback ( 
                  callback, 
                  pub.context, 
                  hasvalue ? _opts['value'] : meta.value, 
                  meta
                );
              });
            },
            successHandler = function(key, meta) {
              //
              // The actual setter gets the real value.
              //
              // If a "coroutine" is set then this will be
              // called before the final setter goes through.
              //
              if (coroutine(meta, true)) {

                //
                // Since the setter normally wraps the meta through a layer
                // of indirection and we have done that already, we need
                // to pass the meta this time as the wrapped version.
                //
                // Otherwise the calling convention of the data getting
                // passed through would magically change if a test gets
                // placed in the chain.
                //
                pub.set ( key, meta.value, meta.meta, {bypass: 1, order: meta.order} );
              } else {
                orHandler();
              }
            },
            // Invoke will also get done
            // but it will have no semantic
            // meaning, so it's fine.
            meta = {};

          meta.old = clone(data[key]);

          extend(meta, {
            // During testing, the setter gets called on success.  We should
            // make sure that our order is continually accumulated if this
            // is part of a re-ingestion.  We make it -1 because we front-load
            // how this is incremented.
            order: ('order' in _opts) ? _opts.order : -1,
            meta: _meta || {},
            key: key,
            _value: hasvalue ? _opts['value'] : meta.value, 
            // the value to set ... or change.
            value: value
          });

          if (doTest) {
            // we permit a level of recursion for testing.
            lockMap[key]--;
            if (testLockMap[key] !== true) {
              testLockMap[key] = true;
              test(key, meta, successHandler, orHandler, coroutine);
              testLockMap[key] = false;
            }

            //
            // Don't return the value...
            // return the current value of that key.
            // 
            // This is because keys can be denied
            result = data[key];
          } else {

            // If there are tracing functions, then we
            // call them one by one
            each ( traceList, function ( callback ) {
              callback.call ( pub.context, args );
            });

            // If there's a coroutine then we call that
            // here
            if (coroutine(meta, true)) {

              value = meta.value;

              //
              // Set the key to the new value.
              // The old value is being passed in
              // through the meta
              //
              // SETTER: This is the actual setting code
              //
              if (!(_opts.onlychange && value === data[key])) {

                if (!_opts.noset) {
                  log(key, value, 'set');
                  data[key] = value;

                  if (key != '') {
                    data_ix[key] = (data_ix[key] || 0) + 1;
                  }
                }

                var myargs = arguments, cback = function (){
                  each(
                    (eventMap[FIRST + key] || []).concat(
                      (eventMap[ON + key] || [])
                    ),
                    function (callback) {
                      meta.last = runCallback(callback, pub.context, value, meta);
                    });

                  // After this, we bubble up if relevant.
                  if (key.length > 0) {
                    // But we don't hit the coroutine
                    delete _opts.coroutine;

                    bubble.apply(pub.context, [key].concat(slice.call(myargs, 2)));
                  }

                  each(eventMap[AFTER + key] || [],
                    function (callback) {
                      meta.last = runCallback(callback, pub.context, value, meta);
                    });

                  lastReturnMap[key] = meta.last;

                  return value;
                }

                if (!noexec) {
                  result = cback.call(pub.context);
                } else {
                  bubble.apply(pub.context, [key].concat(slice.call(myargs, 2)));
                  // if we are not executing this, then
                  // we return a set of functions that we
                  // would be executing.
                  result = cback;
                }
              }
            }
          } 

        } catch(err) {
          throw err;

        } finally {
          lockMap[key] = 0;
        }

        return result;
      },

      fire: function ( key, meta ) {
        each(key, function (what) {
          pub.set ( what, data[what], meta, {noset: true} );
        });
      },

      once: function ( key, lambda, meta ) {
         
        //
        // Permit once to take a bunch of callbacks and mark
        // them all for one time.
        //
        // if we have a 'smart map' then we actually only care
        // about the values of it.
        //
        if ( isObject(key) ) {
          key = values(key);
        }
        if ( isArray(key) ) {
          return map(key, function (what) {
            pub.once.call(pub.context, what, lambda, meta);
          });
        }

        // If this is a callback, then we can register it to be called once.
        if (lambda) {
          // Through some slight recursion.
          return pub.once( 
            // First we register it as normal.
            // Then we call the once with the 
            // handle, returning here
            pub ( key, lambda, meta )

            // And running the function below:
          );
        } 
        // This will add the k/v pair to the handler
        return extend( key, ONCE );
      },

      enable: function ( listName ) {
        each(pub.list[listName], function (callback) {
          if ( callback.norun && callback.norun[listName] ) {
            delete callback.norun[listName];
          }

          if ( size(callback.norun) === 0 ) {
            delete callback.norun;
          }
        });
        return pub.list[listName];
      },

      // This an M*N cost set-add that preserves list 
      // ordinality
      osetadd: function ( key, value, meta ) {
        var before = data[key] || [];

        // If we are successfully adding to the set
        // then we run the events associated with it.
        return pub ( key, value, meta, {
          coroutine: function (meta, isFinal) {
            var valArray = isArray(meta.value) ? meta.value : [meta.value];

            meta.set = clone(before);

            each(valArray, function (what) {
              if (meta.set.indexOf(what) === -1) {
                meta.set.push(what);
              }
            });

            if (isFinal) {
              meta.value = meta.set; 
            }
            meta.oper = {name:'osetadd', value:value};

            return (before.length != meta.set.length);
          }
        });
      },

      toggle: function ( key ) {
        return pub(key, !data[key]);
      },

      // This is a sort + M complexity version that
      // doesn't perserve ordinality.
      setadd: function ( key, value, meta ) {
        var before = data[key] || [];

        return pub( key, value, meta, {
          // this is only called if the tests pass
          coroutine: function (meta, isFinal) {
            var valArray = isArray(meta.value) ? meta.value : [meta.value];
            meta.set = uniq( before.concat(valArray) );

            if (isFinal) {
              meta.value = meta.set; 
            }
            meta.oper = {name:'setadd', value:value};

            return (before.length != meta.set.length);
          }
        });
      },

      settoggle: function ( key, value, meta ) {
        var routine = ((data[key] || []).indexOf(value) === -1) ? 'add' : 'del';
        return pub[SET + routine](key, value, meta);
      },

      setdel: function ( key, value, meta ) {
        var
          before = data[key] || [],
          after = without( before, value);

        if ( before.length != after.length) {
          return pub ( key, after, meta, {
            coroutine: function (meta, isFinal) {
                if (isFinal) {
                  meta.oper = {name:'setdel', value:value};
                }
                return true;
              },
            value: value} );
        }

        return after;
      },

      disable: function ( listName ) {
        each(pub.list[listName], function (callback) {
          ( callback.norun || (callback.norun = {}) ) [ listName ] = true;
        });

        return pub.list[listName];
      },

      unset: function () { 
        var bool = true;
        each(arguments, function (which) {
          bool &= (which in data);

          // This bubbling is totally slow but it works
          var 
            parts = which.split('.'), 
            key = '', 
            len = parts.length,
            last = parts[len - 1],
            ix, iy, 
            ref;

          for (ix = 0; ix < len; ix++) {
            key = parts.slice(0, ix).join('.');
            ref = data[key];
            if (ref) {
              for (iy = ix; iy < (len - 1); iy++) {
                ref = ref[parts[iy]];
              }
              delete ref[last];
            }
          }

          delete data[which];
        });

        return bool;
      },

      find: function ( regex ) {
        return select( keys(data), function (toTest) {
          return toTest.match(regex);
        });
      },

      changed: function (key, callback) {
        return pub.on(key, function (value, meta) {
          var 
            newlen = size(value),
            oldlen = size(meta.old);
          
          if (newlen - oldlen === 1) {
            callback.call( pub.context, last(value) );
          } else if (newlen > oldlen) { 
            callback.call( pub.context, toArray(value).slice(oldlen) );
          }
        });
      },

      version: function() {
        return EvDa.version;
      },
      sniff: function () {
        var 
          ignoreMap = {"":1},
          // Use a few levels of indirection to be
          // able to toggle the sniffing on or off.
          sniffConsole = function (args) {
            // If we are to ignore this then we do nothing,
            // otherwise we console.log when this occurs.
            return ignoreMap[args[0]] || console.log(args);
          },
          dummy = function () {},
          sniffProxy = sniffConsole;

        // sniffProxy either points to sniffConsole
        // when it's on or dummy when it's off.
        traceList.unshift(function (args){
          // That's why we can't call the proxy directly.
          sniffProxy(args);
        });
           
        // neuter this function but don't populate
        // the users keyspace.
        pub.sniff = function () {
          var 
            args = slice.call(arguments), 
            ret = [];

          each(args, function (key) {
            if (isString(key)) {
              if (ignoreMap[key]) {
                delete ignoreMap[key];
              } else {
                ignoreMap[key] = 1;
              }
              ret.push([key, ignoreMap[key]]);

            } else {
              // If the key is true then we turn sniffing "on"
              // by linking the proxy to the real sniff function.
              //
              // Otherwise, we link the proxy to a dummy function
              sniffProxy = key ? sniffConsole : dummy;
              ret.push(key);
            }
          });

          return args.length ? ret : keys(ignoreMap);
        }

        // After we've done the swapping to turn this thing on,
        // now we call the internal function with the args set
        return pub.sniff.apply(pub.context, arguments);
      }
    });

    pub.setAdd = pub.setadd;
    pub.setToggle = pub.settoggle;
    pub.osetAdd = pub.osetadd;
    pub.osetdel = pub.setdel;
    pub.osetDel = pub.setdel;
    pub.setDel = pub.setdel;
    pub.isSet = pub.isset;
    pub.whenset = pub.isset;
    pub.mod = pub.incr;

    pub.get = pub;
    pub.change = pub.on;
    pub.add = pub.push;
    pub.isOK = pub.isok;

    each(e._ext, function (key, cb) {
      pub[key] = function () {
        cb.apply(pub.context, [pub].concat(slice.call(arguments)));
      }
    });

    // After all the mechanisms are set up, then and only then do
    // we do the import
    if (arguments.length > 0) {
      pub(imported);
    }

    return pub;
  }

  e._ext = {};
  e.extend = function (name, cb) {
    e._ext[name] = cb;
  }

  // exposing some internals (mostly for the helper)
  e.isArray = isArray;

  return e;
})();
EvDa.version='0.2.40-20160422';
