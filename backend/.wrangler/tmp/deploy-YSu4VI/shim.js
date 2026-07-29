var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// build/index.js
import { WorkerEntrypoint as st } from "cloudflare:workers";
import B from "./b9030c13f97936eca06e0b79ef5a12c11e7cf468-index_bg.wasm";
import { connect as K } from "cloudflare:sockets";
var _;
var j = null;
function k() {
  return (j === null || j.byteLength === 0) && (j = new Uint8Array(_.memory.buffer)), j;
}
__name(k, "k");
var N = new TextDecoder("utf-8", { ignoreBOM: true, fatal: true });
N.decode();
function Q(t2, e) {
  return N.decode(k().subarray(t2, t2 + e));
}
__name(Q, "Q");
function g(t2, e) {
  return t2 = t2 >>> 0, Q(t2, e);
}
__name(g, "g");
var d = 0;
var W = new TextEncoder();
"encodeInto" in W || (W.encodeInto = function(t2, e) {
  let n = W.encode(t2);
  return e.set(n), { read: t2.length, written: n.length };
});
function p(t2, e, n) {
  if (n === void 0) {
    let a = W.encode(t2), l = e(a.length, 1) >>> 0;
    return k().subarray(l, l + a.length).set(a), d = a.length, l;
  }
  let r = t2.length, o = e(r, 1) >>> 0, b = k(), u = 0;
  for (; u < r; u++) {
    let a = t2.charCodeAt(u);
    if (a > 127) break;
    b[o + u] = a;
  }
  if (u !== r) {
    u !== 0 && (t2 = t2.slice(u)), o = n(o, r, r = u + t2.length * 3, 1) >>> 0;
    let a = k().subarray(o + u, o + r), l = W.encodeInto(t2, a);
    u += l.written, o = n(o, r, u, 1) >>> 0;
  }
  return d = u, o;
}
__name(p, "p");
var y = null;
function f() {
  return (y === null || y.buffer.detached === true || y.buffer.detached === void 0 && y.buffer !== _.memory.buffer) && (y = new DataView(_.memory.buffer)), y;
}
__name(f, "f");
function c(t2) {
  return t2 == null;
}
__name(c, "c");
function T(t2) {
  let e = typeof t2;
  if (e == "number" || e == "boolean" || t2 == null) return `${t2}`;
  if (e == "string") return `"${t2}"`;
  if (e == "symbol") {
    let o = t2.description;
    return o == null ? "Symbol" : `Symbol(${o})`;
  }
  if (e == "function") {
    let o = t2.name;
    return typeof o == "string" && o.length > 0 ? `Function(${o})` : "Function";
  }
  if (Array.isArray(t2)) {
    let o = t2.length, b = "[";
    o > 0 && (b += T(t2[0]));
    for (let u = 1; u < o; u++) b += ", " + T(t2[u]);
    return b += "]", b;
  }
  let n = /\[object ([^\]]+)\]/.exec(toString.call(t2)), r;
  if (n && n.length > 1) r = n[1];
  else return toString.call(t2);
  if (r == "Object") try {
    return "Object(" + JSON.stringify(t2) + ")";
  } catch {
    return "Object";
  }
  return t2 instanceof Error ? `${t2.name}: ${t2.message}
${t2.stack}` : r;
}
__name(T, "T");
function w(t2) {
  let e = _.__externref_table_alloc();
  return _.__wbindgen_externrefs.set(e, t2), e;
}
__name(w, "w");
function s(t2, e) {
  try {
    return t2.apply(this, e);
  } catch (n) {
    let r = w(n);
    _.__wbindgen_exn_store(r);
  }
}
__name(s, "s");
function F(t2, e) {
  return t2 = t2 >>> 0, k().subarray(t2 / 1, t2 / 1 + e);
}
__name(F, "F");
var V = typeof FinalizationRegistry > "u" ? { register: /* @__PURE__ */ __name(() => {
}, "register"), unregister: /* @__PURE__ */ __name(() => {
}, "unregister") } : new FinalizationRegistry((t2) => {
  t2.instance === i && t2.dtor(t2.a, t2.b);
});
function X(t2, e, n, r) {
  let o = { a: t2, b: e, cnt: 1, dtor: n, instance: i }, b = /* @__PURE__ */ __name((...u) => {
    if (o.instance !== i) throw new Error("Cannot invoke closure from previous WASM instance");
    o.cnt++;
    let a = o.a;
    o.a = 0;
    try {
      return r(a, o.b, ...u);
    } finally {
      o.a = a, b._wbg_cb_unref();
    }
  }, "b");
  return b._wbg_cb_unref = () => {
    --o.cnt === 0 && (o.dtor(o.a, o.b), o.a = 0, V.unregister(o));
  }, V.register(b, o, o), b;
}
__name(X, "X");
function J(t2, e, n) {
  return _.fetch(t2, e, n);
}
__name(J, "J");
function Y(t2, e, n) {
  _.wasm_bindgen_27cce28d972db99d___convert__closures_____invoke___wasm_bindgen_27cce28d972db99d___JsValue_____(t2, e, n);
}
__name(Y, "Y");
function Z(t2, e, n, r) {
  _.wasm_bindgen_27cce28d972db99d___convert__closures_____invoke___wasm_bindgen_27cce28d972db99d___JsValue__wasm_bindgen_27cce28d972db99d___JsValue_____(t2, e, n, r);
}
__name(Z, "Z");
var at = Object.freeze({ Off: 0, 0: "Off", Lossy: 1, 1: "Lossy", Lossless: 2, 2: "Lossless" });
var bt = Object.freeze({ Error: 0, 0: "Error", Follow: 1, 1: "Follow", Manual: 2, 2: "Manual" });
var tt = ["bytes"];
var et = ["follow", "error", "manual"];
var i = 0;
function H() {
  i++, y = null, j = null, typeof numBytesDecoded < "u" && (numBytesDecoded = 0), typeof d < "u" && (d = 0), _ = new WebAssembly.Instance(B, $).exports, _.__wbindgen_start();
}
__name(H, "H");
var q = typeof FinalizationRegistry > "u" ? { register: /* @__PURE__ */ __name(() => {
}, "register"), unregister: /* @__PURE__ */ __name(() => {
}, "unregister") } : new FinalizationRegistry(({ ptr: t2, instance: e }) => {
  e === i && _.__wbg_chatstate_free(t2 >>> 0, 1);
});
var x = class {
  static {
    __name(this, "x");
  }
  __destroy_into_raw() {
    let e = this.__wbg_ptr;
    return this.__wbg_ptr = 0, q.unregister(this), e;
  }
  free() {
    let e = this.__destroy_into_raw();
    _.__wbg_chatstate_free(e, 0);
  }
  constructor(e, n) {
    let r = _.chatstate__new(e, n);
    return this.__wbg_ptr = r >>> 0, this.__wbg_inst = i, q.register(this, { ptr: r >>> 0, instance: i }, this), this;
  }
  fetch(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    return _.chatstate_fetch(this.__wbg_ptr, e);
  }
};
Symbol.dispose && (x.prototype[Symbol.dispose] = x.prototype.free);
var nt = typeof FinalizationRegistry > "u" ? { register: /* @__PURE__ */ __name(() => {
}, "register"), unregister: /* @__PURE__ */ __name(() => {
}, "unregister") } : new FinalizationRegistry(({ ptr: t2, instance: e }) => {
  e === i && _.__wbg_intounderlyingbytesource_free(t2 >>> 0, 1);
});
var R = class {
  static {
    __name(this, "R");
  }
  __destroy_into_raw() {
    let e = this.__wbg_ptr;
    return this.__wbg_ptr = 0, nt.unregister(this), e;
  }
  free() {
    let e = this.__destroy_into_raw();
    _.__wbg_intounderlyingbytesource_free(e, 0);
  }
  get autoAllocateChunkSize() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    return _.intounderlyingbytesource_autoAllocateChunkSize(this.__wbg_ptr) >>> 0;
  }
  pull(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    return _.intounderlyingbytesource_pull(this.__wbg_ptr, e);
  }
  start(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    _.intounderlyingbytesource_start(this.__wbg_ptr, e);
  }
  get type() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    let e = _.intounderlyingbytesource_type(this.__wbg_ptr);
    return tt[e];
  }
  cancel() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    let e = this.__destroy_into_raw();
    _.intounderlyingbytesource_cancel(e);
  }
};
Symbol.dispose && (R.prototype[Symbol.dispose] = R.prototype.free);
var rt = typeof FinalizationRegistry > "u" ? { register: /* @__PURE__ */ __name(() => {
}, "register"), unregister: /* @__PURE__ */ __name(() => {
}, "unregister") } : new FinalizationRegistry(({ ptr: t2, instance: e }) => {
  e === i && _.__wbg_intounderlyingsink_free(t2 >>> 0, 1);
});
var I = class {
  static {
    __name(this, "I");
  }
  __destroy_into_raw() {
    let e = this.__wbg_ptr;
    return this.__wbg_ptr = 0, rt.unregister(this), e;
  }
  free() {
    let e = this.__destroy_into_raw();
    _.__wbg_intounderlyingsink_free(e, 0);
  }
  abort(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    let n = this.__destroy_into_raw();
    return _.intounderlyingsink_abort(n, e);
  }
  close() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    let e = this.__destroy_into_raw();
    return _.intounderlyingsink_close(e);
  }
  write(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    return _.intounderlyingsink_write(this.__wbg_ptr, e);
  }
};
Symbol.dispose && (I.prototype[Symbol.dispose] = I.prototype.free);
var _t = typeof FinalizationRegistry > "u" ? { register: /* @__PURE__ */ __name(() => {
}, "register"), unregister: /* @__PURE__ */ __name(() => {
}, "unregister") } : new FinalizationRegistry(({ ptr: t2, instance: e }) => {
  e === i && _.__wbg_intounderlyingsource_free(t2 >>> 0, 1);
});
var v = class {
  static {
    __name(this, "v");
  }
  __destroy_into_raw() {
    let e = this.__wbg_ptr;
    return this.__wbg_ptr = 0, _t.unregister(this), e;
  }
  free() {
    let e = this.__destroy_into_raw();
    _.__wbg_intounderlyingsource_free(e, 0);
  }
  pull(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    return _.intounderlyingsource_pull(this.__wbg_ptr, e);
  }
  cancel() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    let e = this.__destroy_into_raw();
    _.intounderlyingsource_cancel(e);
  }
};
Symbol.dispose && (v.prototype[Symbol.dispose] = v.prototype.free);
var D = typeof FinalizationRegistry > "u" ? { register: /* @__PURE__ */ __name(() => {
}, "register"), unregister: /* @__PURE__ */ __name(() => {
}, "unregister") } : new FinalizationRegistry(({ ptr: t2, instance: e }) => {
  e === i && _.__wbg_minifyconfig_free(t2 >>> 0, 1);
});
var h = class t {
  static {
    __name(this, "t");
  }
  static __wrap(e) {
    e = e >>> 0;
    let n = Object.create(t.prototype);
    return n.__wbg_ptr = e, n.__wbg_inst = i, D.register(n, { ptr: e, instance: i }, n), n;
  }
  __destroy_into_raw() {
    let e = this.__wbg_ptr;
    return this.__wbg_ptr = 0, D.unregister(this), e;
  }
  free() {
    let e = this.__destroy_into_raw();
    _.__wbg_minifyconfig_free(e, 0);
  }
  get js() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    return _.__wbg_get_minifyconfig_js(this.__wbg_ptr) !== 0;
  }
  set js(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    _.__wbg_set_minifyconfig_js(this.__wbg_ptr, e);
  }
  get html() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    return _.__wbg_get_minifyconfig_html(this.__wbg_ptr) !== 0;
  }
  set html(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    _.__wbg_set_minifyconfig_html(this.__wbg_ptr, e);
  }
  get css() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    return _.__wbg_get_minifyconfig_css(this.__wbg_ptr) !== 0;
  }
  set css(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    _.__wbg_set_minifyconfig_css(this.__wbg_ptr, e);
  }
};
Symbol.dispose && (h.prototype[Symbol.dispose] = h.prototype.free);
var ot = typeof FinalizationRegistry > "u" ? { register: /* @__PURE__ */ __name(() => {
}, "register"), unregister: /* @__PURE__ */ __name(() => {
}, "unregister") } : new FinalizationRegistry(({ ptr: t2, instance: e }) => {
  e === i && _.__wbg_r2range_free(t2 >>> 0, 1);
});
var E = class {
  static {
    __name(this, "E");
  }
  __destroy_into_raw() {
    let e = this.__wbg_ptr;
    return this.__wbg_ptr = 0, ot.unregister(this), e;
  }
  free() {
    let e = this.__destroy_into_raw();
    _.__wbg_r2range_free(e, 0);
  }
  get offset() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    let e = _.__wbg_get_r2range_offset(this.__wbg_ptr);
    return e[0] === 0 ? void 0 : e[1];
  }
  set offset(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    _.__wbg_set_r2range_offset(this.__wbg_ptr, !c(e), c(e) ? 0 : e);
  }
  get length() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    let e = _.__wbg_get_r2range_length(this.__wbg_ptr);
    return e[0] === 0 ? void 0 : e[1];
  }
  set length(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    _.__wbg_set_r2range_length(this.__wbg_ptr, !c(e), c(e) ? 0 : e);
  }
  get suffix() {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    let e = _.__wbg_get_r2range_suffix(this.__wbg_ptr);
    return e[0] === 0 ? void 0 : e[1];
  }
  set suffix(e) {
    if (this.__wbg_inst !== void 0 && this.__wbg_inst !== i) throw new Error("Invalid stale object from previous Wasm instance");
    _.__wbg_set_r2range_suffix(this.__wbg_ptr, !c(e), c(e) ? 0 : e);
  }
};
Symbol.dispose && (E.prototype[Symbol.dispose] = E.prototype.free);
var $ = { __wbindgen_placeholder__: { __wbg_Error_e83987f665cf5504: /* @__PURE__ */ __name(function(t2, e) {
  return Error(g(t2, e));
}, "__wbg_Error_e83987f665cf5504"), __wbg_Number_bb48ca12f395cd08: /* @__PURE__ */ __name(function(t2) {
  return Number(t2);
}, "__wbg_Number_bb48ca12f395cd08"), __wbg_String_8f0eb39a4a4c2f66: /* @__PURE__ */ __name(function(t2, e) {
  let n = String(e), r = p(n, _.__wbindgen_malloc, _.__wbindgen_realloc), o = d;
  f().setInt32(t2 + 4, o, true), f().setInt32(t2 + 0, r, true);
}, "__wbg_String_8f0eb39a4a4c2f66"), __wbg___wbindgen_bigint_get_as_i64_f3ebc5a755000afd: /* @__PURE__ */ __name(function(t2, e) {
  let n = e, r = typeof n == "bigint" ? n : void 0;
  f().setBigInt64(t2 + 8, c(r) ? BigInt(0) : r, true), f().setInt32(t2 + 0, !c(r), true);
}, "__wbg___wbindgen_bigint_get_as_i64_f3ebc5a755000afd"), __wbg___wbindgen_boolean_get_6d5a1ee65bab5f68: /* @__PURE__ */ __name(function(t2) {
  let e = t2, n = typeof e == "boolean" ? e : void 0;
  return c(n) ? 16777215 : n ? 1 : 0;
}, "__wbg___wbindgen_boolean_get_6d5a1ee65bab5f68"), __wbg___wbindgen_debug_string_df47ffb5e35e6763: /* @__PURE__ */ __name(function(t2, e) {
  let n = T(e), r = p(n, _.__wbindgen_malloc, _.__wbindgen_realloc), o = d;
  f().setInt32(t2 + 4, o, true), f().setInt32(t2 + 0, r, true);
}, "__wbg___wbindgen_debug_string_df47ffb5e35e6763"), __wbg___wbindgen_in_bb933bd9e1b3bc0f: /* @__PURE__ */ __name(function(t2, e) {
  return t2 in e;
}, "__wbg___wbindgen_in_bb933bd9e1b3bc0f"), __wbg___wbindgen_is_bigint_cb320707dcd35f0b: /* @__PURE__ */ __name(function(t2) {
  return typeof t2 == "bigint";
}, "__wbg___wbindgen_is_bigint_cb320707dcd35f0b"), __wbg___wbindgen_is_falsy_46b8d2f2aba49112: /* @__PURE__ */ __name(function(t2) {
  return !t2;
}, "__wbg___wbindgen_is_falsy_46b8d2f2aba49112"), __wbg___wbindgen_is_function_ee8a6c5833c90377: /* @__PURE__ */ __name(function(t2) {
  return typeof t2 == "function";
}, "__wbg___wbindgen_is_function_ee8a6c5833c90377"), __wbg___wbindgen_is_object_c818261d21f283a4: /* @__PURE__ */ __name(function(t2) {
  let e = t2;
  return typeof e == "object" && e !== null;
}, "__wbg___wbindgen_is_object_c818261d21f283a4"), __wbg___wbindgen_is_string_fbb76cb2940daafd: /* @__PURE__ */ __name(function(t2) {
  return typeof t2 == "string";
}, "__wbg___wbindgen_is_string_fbb76cb2940daafd"), __wbg___wbindgen_is_undefined_2d472862bd29a478: /* @__PURE__ */ __name(function(t2) {
  return t2 === void 0;
}, "__wbg___wbindgen_is_undefined_2d472862bd29a478"), __wbg___wbindgen_jsval_eq_6b13ab83478b1c50: /* @__PURE__ */ __name(function(t2, e) {
  return t2 === e;
}, "__wbg___wbindgen_jsval_eq_6b13ab83478b1c50"), __wbg___wbindgen_jsval_loose_eq_b664b38a2f582147: /* @__PURE__ */ __name(function(t2, e) {
  return t2 == e;
}, "__wbg___wbindgen_jsval_loose_eq_b664b38a2f582147"), __wbg___wbindgen_number_get_a20bf9b85341449d: /* @__PURE__ */ __name(function(t2, e) {
  let n = e, r = typeof n == "number" ? n : void 0;
  f().setFloat64(t2 + 8, c(r) ? 0 : r, true), f().setInt32(t2 + 0, !c(r), true);
}, "__wbg___wbindgen_number_get_a20bf9b85341449d"), __wbg___wbindgen_string_get_e4f06c90489ad01b: /* @__PURE__ */ __name(function(t2, e) {
  let n = e, r = typeof n == "string" ? n : void 0;
  var o = c(r) ? 0 : p(r, _.__wbindgen_malloc, _.__wbindgen_realloc), b = d;
  f().setInt32(t2 + 4, b, true), f().setInt32(t2 + 0, o, true);
}, "__wbg___wbindgen_string_get_e4f06c90489ad01b"), __wbg___wbindgen_throw_b855445ff6a94295: /* @__PURE__ */ __name(function(t2, e) {
  throw new Error(g(t2, e));
}, "__wbg___wbindgen_throw_b855445ff6a94295"), __wbg__wbg_cb_unref_2454a539ea5790d9: /* @__PURE__ */ __name(function(t2) {
  t2._wbg_cb_unref();
}, "__wbg__wbg_cb_unref_2454a539ea5790d9"), __wbg_body_587542b2fd8e06c0: /* @__PURE__ */ __name(function(t2) {
  let e = t2.body;
  return c(e) ? 0 : w(e);
}, "__wbg_body_587542b2fd8e06c0"), __wbg_buffer_ccc4520b36d3ccf4: /* @__PURE__ */ __name(function(t2) {
  return t2.buffer;
}, "__wbg_buffer_ccc4520b36d3ccf4"), __wbg_byobRequest_2344e6975f27456e: /* @__PURE__ */ __name(function(t2) {
  let e = t2.byobRequest;
  return c(e) ? 0 : w(e);
}, "__wbg_byobRequest_2344e6975f27456e"), __wbg_byteLength_bcd42e4025299788: /* @__PURE__ */ __name(function(t2) {
  return t2.byteLength;
}, "__wbg_byteLength_bcd42e4025299788"), __wbg_byteOffset_ca3a6cf7944b364b: /* @__PURE__ */ __name(function(t2) {
  return t2.byteOffset;
}, "__wbg_byteOffset_ca3a6cf7944b364b"), __wbg_call_525440f72fbfc0ea: /* @__PURE__ */ __name(function() {
  return s(function(t2, e, n) {
    return t2.call(e, n);
  }, arguments);
}, "__wbg_call_525440f72fbfc0ea"), __wbg_call_e762c39fa8ea36bf: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    return t2.call(e);
  }, arguments);
}, "__wbg_call_e762c39fa8ea36bf"), __wbg_cancel_48ab6f9dc366e369: /* @__PURE__ */ __name(function(t2) {
  return t2.cancel();
}, "__wbg_cancel_48ab6f9dc366e369"), __wbg_catch_943836faa5d29bfb: /* @__PURE__ */ __name(function(t2, e) {
  return t2.catch(e);
}, "__wbg_catch_943836faa5d29bfb"), __wbg_cause_2551549fc39b3b73: /* @__PURE__ */ __name(function(t2) {
  return t2.cause;
}, "__wbg_cause_2551549fc39b3b73"), __wbg_cf_14f2f56599b2a66f: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    let e = t2.cf;
    return c(e) ? 0 : w(e);
  }, arguments);
}, "__wbg_cf_14f2f56599b2a66f"), __wbg_cf_dc4bf2e09a6a0fc0: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    let e = t2.cf;
    return c(e) ? 0 : w(e);
  }, arguments);
}, "__wbg_cf_dc4bf2e09a6a0fc0"), __wbg_close_5a6caed3231b68cd: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    t2.close();
  }, arguments);
}, "__wbg_close_5a6caed3231b68cd"), __wbg_close_6956df845478561a: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    t2.close();
  }, arguments);
}, "__wbg_close_6956df845478561a"), __wbg_close_dd3c97459a36cc60: /* @__PURE__ */ __name(function(t2) {
  return t2.close();
}, "__wbg_close_dd3c97459a36cc60"), __wbg_connect_7fda407c9690d7b0: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    return K(t2, e);
  }, arguments);
}, "__wbg_connect_7fda407c9690d7b0"), __wbg_constructor_43c608587565cd11: /* @__PURE__ */ __name(function(t2) {
  return t2.constructor;
}, "__wbg_constructor_43c608587565cd11"), __wbg_database_e72318a0046f6511: /* @__PURE__ */ __name(function(t2, e) {
  let n = e.database, r = p(n, _.__wbindgen_malloc, _.__wbindgen_realloc), o = d;
  f().setInt32(t2 + 4, o, true), f().setInt32(t2 + 0, r, true);
}, "__wbg_database_e72318a0046f6511"), __wbg_done_2042aa2670fb1db1: /* @__PURE__ */ __name(function(t2) {
  return t2.done;
}, "__wbg_done_2042aa2670fb1db1"), __wbg_enqueue_7b18a650aec77898: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    t2.enqueue(e);
  }, arguments);
}, "__wbg_enqueue_7b18a650aec77898"), __wbg_error_a7f8fbb0523dae15: /* @__PURE__ */ __name(function(t2) {
  console.error(t2);
}, "__wbg_error_a7f8fbb0523dae15"), __wbg_fetch_8725865ff47e7fcc: /* @__PURE__ */ __name(function(t2, e, n) {
  return t2.fetch(e, n);
}, "__wbg_fetch_8725865ff47e7fcc"), __wbg_fetch_a33defa4cad834df: /* @__PURE__ */ __name(function(t2, e, n, r) {
  return t2.fetch(g(e, n), r);
}, "__wbg_fetch_a33defa4cad834df"), __wbg_fetch_d8a7b00b16a946ac: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    return t2.fetch(e);
  }, arguments);
}, "__wbg_fetch_d8a7b00b16a946ac"), __wbg_getRandomValues_4d6521d092b50cf5: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    globalThis.crypto.getRandomValues(F(t2, e));
  }, arguments);
}, "__wbg_getRandomValues_4d6521d092b50cf5"), __wbg_getRandomValues_a8ddca022803a145: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    globalThis.crypto.getRandomValues(F(t2, e));
  }, arguments);
}, "__wbg_getRandomValues_a8ddca022803a145"), __wbg_getReader_15e2d3098e32c359: /* @__PURE__ */ __name(function(t2) {
  return t2.getReader();
}, "__wbg_getReader_15e2d3098e32c359"), __wbg_getReader_48e00749fe3f6089: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    return t2.getReader();
  }, arguments);
}, "__wbg_getReader_48e00749fe3f6089"), __wbg_getWriter_c891ce50cc187493: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    return t2.getWriter();
  }, arguments);
}, "__wbg_getWriter_c891ce50cc187493"), __wbg_get_7bed016f185add81: /* @__PURE__ */ __name(function(t2, e) {
  return t2[e >>> 0];
}, "__wbg_get_7bed016f185add81"), __wbg_get_8fa4f245e13d8fd7: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    return t2.get(e);
  }, arguments);
}, "__wbg_get_8fa4f245e13d8fd7"), __wbg_get_done_a0463af43a1fc764: /* @__PURE__ */ __name(function(t2) {
  let e = t2.done;
  return c(e) ? 16777215 : e ? 1 : 0;
}, "__wbg_get_done_a0463af43a1fc764"), __wbg_get_efcb449f58ec27c2: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    return Reflect.get(t2, e);
  }, arguments);
}, "__wbg_get_efcb449f58ec27c2"), __wbg_get_value_5ce96c9f81ce7398: /* @__PURE__ */ __name(function(t2) {
  return t2.value;
}, "__wbg_get_value_5ce96c9f81ce7398"), __wbg_get_with_ref_key_1dc361bd10053bfe: /* @__PURE__ */ __name(function(t2, e) {
  return t2[e];
}, "__wbg_get_with_ref_key_1dc361bd10053bfe"), __wbg_headers_7ae6dbb1272f8fc6: /* @__PURE__ */ __name(function(t2) {
  return t2.headers;
}, "__wbg_headers_7ae6dbb1272f8fc6"), __wbg_headers_b87d7eaba61c3278: /* @__PURE__ */ __name(function(t2) {
  return t2.headers;
}, "__wbg_headers_b87d7eaba61c3278"), __wbg_host_84cdfdef9472d63e: /* @__PURE__ */ __name(function(t2, e) {
  let n = e.host, r = p(n, _.__wbindgen_malloc, _.__wbindgen_realloc), o = d;
  f().setInt32(t2 + 4, o, true), f().setInt32(t2 + 0, r, true);
}, "__wbg_host_84cdfdef9472d63e"), __wbg_idFromName_b3634db46c1bce69: /* @__PURE__ */ __name(function() {
  return s(function(t2, e, n) {
    return t2.idFromName(g(e, n));
  }, arguments);
}, "__wbg_idFromName_b3634db46c1bce69"), __wbg_instanceof_ArrayBuffer_70beb1189ca63b38: /* @__PURE__ */ __name(function(t2) {
  let e;
  try {
    e = t2 instanceof ArrayBuffer;
  } catch {
    e = false;
  }
  return e;
}, "__wbg_instanceof_ArrayBuffer_70beb1189ca63b38"), __wbg_instanceof_Error_a944ec10920129e2: /* @__PURE__ */ __name(function(t2) {
  let e;
  try {
    e = t2 instanceof Error;
  } catch {
    e = false;
  }
  return e;
}, "__wbg_instanceof_Error_a944ec10920129e2"), __wbg_instanceof_ReadableStreamDefaultReader_33a4601dd218c69d: /* @__PURE__ */ __name(function(t2) {
  let e;
  try {
    e = t2 instanceof ReadableStreamDefaultReader;
  } catch {
    e = false;
  }
  return e;
}, "__wbg_instanceof_ReadableStreamDefaultReader_33a4601dd218c69d"), __wbg_instanceof_ReadableStream_c34776a5fb889c65: /* @__PURE__ */ __name(function(t2) {
  let e;
  try {
    e = t2 instanceof ReadableStream;
  } catch {
    e = false;
  }
  return e;
}, "__wbg_instanceof_ReadableStream_c34776a5fb889c65"), __wbg_instanceof_Response_f4f3e87e07f3135c: /* @__PURE__ */ __name(function(t2) {
  let e;
  try {
    e = t2 instanceof Response;
  } catch {
    e = false;
  }
  return e;
}, "__wbg_instanceof_Response_f4f3e87e07f3135c"), __wbg_instanceof_Uint8Array_20c8e73002f7af98: /* @__PURE__ */ __name(function(t2) {
  let e;
  try {
    e = t2 instanceof Uint8Array;
  } catch {
    e = false;
  }
  return e;
}, "__wbg_instanceof_Uint8Array_20c8e73002f7af98"), __wbg_isArray_96e0af9891d0945d: /* @__PURE__ */ __name(function(t2) {
  return Array.isArray(t2);
}, "__wbg_isArray_96e0af9891d0945d"), __wbg_isSafeInteger_d216eda7911dde36: /* @__PURE__ */ __name(function(t2) {
  return Number.isSafeInteger(t2);
}, "__wbg_isSafeInteger_d216eda7911dde36"), __wbg_iterator_e5822695327a3c39: /* @__PURE__ */ __name(function() {
  return Symbol.iterator;
}, "__wbg_iterator_e5822695327a3c39"), __wbg_json_2a5b6569e1c7a50f: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    return t2.json();
  }, arguments);
}, "__wbg_json_2a5b6569e1c7a50f"), __wbg_length_69bca3cb64fc8748: /* @__PURE__ */ __name(function(t2) {
  return t2.length;
}, "__wbg_length_69bca3cb64fc8748"), __wbg_length_cdd215e10d9dd507: /* @__PURE__ */ __name(function(t2) {
  return t2.length;
}, "__wbg_length_cdd215e10d9dd507"), __wbg_method_07a9b3454994db22: /* @__PURE__ */ __name(function(t2, e) {
  let n = e.method, r = p(n, _.__wbindgen_malloc, _.__wbindgen_realloc), o = d;
  f().setInt32(t2 + 4, o, true), f().setInt32(t2 + 0, r, true);
}, "__wbg_method_07a9b3454994db22"), __wbg_minifyconfig_new: /* @__PURE__ */ __name(function(t2) {
  return h.__wrap(t2);
}, "__wbg_minifyconfig_new"), __wbg_name_5383f8ff646a0ac1: /* @__PURE__ */ __name(function(t2) {
  return t2.name;
}, "__wbg_name_5383f8ff646a0ac1"), __wbg_new_1acc0b6eea89d040: /* @__PURE__ */ __name(function() {
  return new Object();
}, "__wbg_new_1acc0b6eea89d040"), __wbg_new_3c3d849046688a66: /* @__PURE__ */ __name(function(t2, e) {
  try {
    var n = { a: t2, b: e }, r = /* @__PURE__ */ __name((b, u) => {
      let a = n.a;
      n.a = 0;
      try {
        return Z(a, n.b, b, u);
      } finally {
        n.a = a;
      }
    }, "r");
    return new Promise(r);
  } finally {
    n.a = n.b = 0;
  }
}, "__wbg_new_3c3d849046688a66"), __wbg_new_5a79be3ab53b8aa5: /* @__PURE__ */ __name(function(t2) {
  return new Uint8Array(t2);
}, "__wbg_new_5a79be3ab53b8aa5"), __wbg_new_68651c719dcda04e: /* @__PURE__ */ __name(function() {
  return /* @__PURE__ */ new Map();
}, "__wbg_new_68651c719dcda04e"), __wbg_new_9edf9838a2def39c: /* @__PURE__ */ __name(function() {
  return s(function() {
    return new Headers();
  }, arguments);
}, "__wbg_new_9edf9838a2def39c"), __wbg_new_a7442b4b19c1a356: /* @__PURE__ */ __name(function(t2, e) {
  return new Error(g(t2, e));
}, "__wbg_new_a7442b4b19c1a356"), __wbg_new_from_slice_92f4d78ca282a2d2: /* @__PURE__ */ __name(function(t2, e) {
  return new Uint8Array(F(t2, e));
}, "__wbg_new_from_slice_92f4d78ca282a2d2"), __wbg_new_no_args_ee98eee5275000a4: /* @__PURE__ */ __name(function(t2, e) {
  return new Function(g(t2, e));
}, "__wbg_new_no_args_ee98eee5275000a4"), __wbg_new_with_byte_offset_and_length_46e3e6a5e9f9e89b: /* @__PURE__ */ __name(function(t2, e, n) {
  return new Uint8Array(t2, e >>> 0, n >>> 0);
}, "__wbg_new_with_byte_offset_and_length_46e3e6a5e9f9e89b"), __wbg_new_with_length_01aa0dc35aa13543: /* @__PURE__ */ __name(function(t2) {
  return new Uint8Array(t2 >>> 0);
}, "__wbg_new_with_length_01aa0dc35aa13543"), __wbg_new_with_opt_buffer_source_and_init_d7e792cdf59c8ea6: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    return new Response(t2, e);
  }, arguments);
}, "__wbg_new_with_opt_buffer_source_and_init_d7e792cdf59c8ea6"), __wbg_new_with_opt_readable_stream_and_init_b3dac7204db32cac: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    return new Response(t2, e);
  }, arguments);
}, "__wbg_new_with_opt_readable_stream_and_init_b3dac7204db32cac"), __wbg_new_with_opt_str_and_init_271896583401be6f: /* @__PURE__ */ __name(function() {
  return s(function(t2, e, n) {
    return new Response(t2 === 0 ? void 0 : g(t2, e), n);
  }, arguments);
}, "__wbg_new_with_opt_str_and_init_271896583401be6f"), __wbg_new_with_str_and_init_0ae7728b6ec367b1: /* @__PURE__ */ __name(function() {
  return s(function(t2, e, n) {
    return new Request(g(t2, e), n);
  }, arguments);
}, "__wbg_new_with_str_and_init_0ae7728b6ec367b1"), __wbg_next_020810e0ae8ebcb0: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    return t2.next();
  }, arguments);
}, "__wbg_next_020810e0ae8ebcb0"), __wbg_next_2c826fe5dfec6b6a: /* @__PURE__ */ __name(function(t2) {
  return t2.next;
}, "__wbg_next_2c826fe5dfec6b6a"), __wbg_password_9b5ef0ac289ddd90: /* @__PURE__ */ __name(function(t2, e) {
  let n = e.password, r = p(n, _.__wbindgen_malloc, _.__wbindgen_realloc), o = d;
  f().setInt32(t2 + 4, o, true), f().setInt32(t2 + 0, r, true);
}, "__wbg_password_9b5ef0ac289ddd90"), __wbg_port_05eeac48d7bbca47: /* @__PURE__ */ __name(function(t2) {
  return t2.port;
}, "__wbg_port_05eeac48d7bbca47"), __wbg_prototypesetcall_2a6620b6922694b2: /* @__PURE__ */ __name(function(t2, e, n) {
  Uint8Array.prototype.set.call(F(t2, e), n);
}, "__wbg_prototypesetcall_2a6620b6922694b2"), __wbg_queueMicrotask_34d692c25c47d05b: /* @__PURE__ */ __name(function(t2) {
  return t2.queueMicrotask;
}, "__wbg_queueMicrotask_34d692c25c47d05b"), __wbg_queueMicrotask_9d76cacb20c84d58: /* @__PURE__ */ __name(function(t2) {
  queueMicrotask(t2);
}, "__wbg_queueMicrotask_9d76cacb20c84d58"), __wbg_read_48f1593df542f968: /* @__PURE__ */ __name(function(t2) {
  return t2.read();
}, "__wbg_read_48f1593df542f968"), __wbg_readable_f99113b65bc696ea: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    return t2.readable;
  }, arguments);
}, "__wbg_readable_f99113b65bc696ea"), __wbg_releaseLock_5d0b5a68887b891d: /* @__PURE__ */ __name(function(t2) {
  t2.releaseLock();
}, "__wbg_releaseLock_5d0b5a68887b891d"), __wbg_releaseLock_b6532de53da4cce6: /* @__PURE__ */ __name(function(t2) {
  t2.releaseLock();
}, "__wbg_releaseLock_b6532de53da4cce6"), __wbg_resolve_caf97c30b83f7053: /* @__PURE__ */ __name(function(t2) {
  return Promise.resolve(t2);
}, "__wbg_resolve_caf97c30b83f7053"), __wbg_respond_0f4dbf5386f5c73e: /* @__PURE__ */ __name(function() {
  return s(function(t2, e) {
    t2.respond(e >>> 0);
  }, arguments);
}, "__wbg_respond_0f4dbf5386f5c73e"), __wbg_set_3f1d0b984ed272ed: /* @__PURE__ */ __name(function(t2, e, n) {
  t2[e] = n;
}, "__wbg_set_3f1d0b984ed272ed"), __wbg_set_8b342d8cd9d2a02c: /* @__PURE__ */ __name(function() {
  return s(function(t2, e, n, r, o) {
    t2.set(g(e, n), g(r, o));
  }, arguments);
}, "__wbg_set_8b342d8cd9d2a02c"), __wbg_set_907fb406c34a251d: /* @__PURE__ */ __name(function(t2, e, n) {
  return t2.set(e, n);
}, "__wbg_set_907fb406c34a251d"), __wbg_set_9e6516df7b7d0f19: /* @__PURE__ */ __name(function(t2, e, n) {
  t2.set(F(e, n));
}, "__wbg_set_9e6516df7b7d0f19"), __wbg_set_body_3c365989753d61f4: /* @__PURE__ */ __name(function(t2, e) {
  t2.body = e;
}, "__wbg_set_body_3c365989753d61f4"), __wbg_set_c2abbebe8b9ebee1: /* @__PURE__ */ __name(function() {
  return s(function(t2, e, n) {
    return Reflect.set(t2, e, n);
  }, arguments);
}, "__wbg_set_c2abbebe8b9ebee1"), __wbg_set_headers_107379072e02fee5: /* @__PURE__ */ __name(function(t2, e) {
  t2.headers = e;
}, "__wbg_set_headers_107379072e02fee5"), __wbg_set_headers_6926da238cd32ee4: /* @__PURE__ */ __name(function(t2, e) {
  t2.headers = e;
}, "__wbg_set_headers_6926da238cd32ee4"), __wbg_set_method_c02d8cbbe204ac2d: /* @__PURE__ */ __name(function(t2, e, n) {
  t2.method = g(e, n);
}, "__wbg_set_method_c02d8cbbe204ac2d"), __wbg_set_redirect_df0285496ec45ff8: /* @__PURE__ */ __name(function(t2, e) {
  t2.redirect = et[e];
}, "__wbg_set_redirect_df0285496ec45ff8"), __wbg_set_signal_dda2cf7ccb6bee0f: /* @__PURE__ */ __name(function(t2, e) {
  t2.signal = e;
}, "__wbg_set_signal_dda2cf7ccb6bee0f"), __wbg_set_status_886bf143c25d0706: /* @__PURE__ */ __name(function(t2, e) {
  t2.status = e;
}, "__wbg_set_status_886bf143c25d0706"), __wbg_startTls_8a514ac93475b9f6: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    return t2.startTls();
  }, arguments);
}, "__wbg_startTls_8a514ac93475b9f6"), __wbg_static_accessor_GLOBAL_89e1d9ac6a1b250e: /* @__PURE__ */ __name(function() {
  let t2 = typeof global > "u" ? null : global;
  return c(t2) ? 0 : w(t2);
}, "__wbg_static_accessor_GLOBAL_89e1d9ac6a1b250e"), __wbg_static_accessor_GLOBAL_THIS_8b530f326a9e48ac: /* @__PURE__ */ __name(function() {
  let t2 = typeof globalThis > "u" ? null : globalThis;
  return c(t2) ? 0 : w(t2);
}, "__wbg_static_accessor_GLOBAL_THIS_8b530f326a9e48ac"), __wbg_static_accessor_SELF_6fdf4b64710cc91b: /* @__PURE__ */ __name(function() {
  let t2 = typeof self > "u" ? null : self;
  return c(t2) ? 0 : w(t2);
}, "__wbg_static_accessor_SELF_6fdf4b64710cc91b"), __wbg_static_accessor_WINDOW_b45bfc5a37f6cfa2: /* @__PURE__ */ __name(function() {
  let t2 = typeof window > "u" ? null : window;
  return c(t2) ? 0 : w(t2);
}, "__wbg_static_accessor_WINDOW_b45bfc5a37f6cfa2"), __wbg_status_de7eed5a7a5bfd5d: /* @__PURE__ */ __name(function(t2) {
  return t2.status;
}, "__wbg_status_de7eed5a7a5bfd5d"), __wbg_then_4f46f6544e6b4a28: /* @__PURE__ */ __name(function(t2, e) {
  return t2.then(e);
}, "__wbg_then_4f46f6544e6b4a28"), __wbg_then_70d05cf780a18d77: /* @__PURE__ */ __name(function(t2, e, n) {
  return t2.then(e, n);
}, "__wbg_then_70d05cf780a18d77"), __wbg_toString_8eec07f6f4c057e4: /* @__PURE__ */ __name(function(t2) {
  return t2.toString();
}, "__wbg_toString_8eec07f6f4c057e4"), __wbg_url_3e15bfb59fa6b660: /* @__PURE__ */ __name(function(t2, e) {
  let n = e.url, r = p(n, _.__wbindgen_malloc, _.__wbindgen_realloc), o = d;
  f().setInt32(t2 + 4, o, true), f().setInt32(t2 + 0, r, true);
}, "__wbg_url_3e15bfb59fa6b660"), __wbg_user_1c95d1e5eb0c1bb8: /* @__PURE__ */ __name(function(t2, e) {
  let n = e.user, r = p(n, _.__wbindgen_malloc, _.__wbindgen_realloc), o = d;
  f().setInt32(t2 + 4, o, true), f().setInt32(t2 + 0, r, true);
}, "__wbg_user_1c95d1e5eb0c1bb8"), __wbg_value_692627309814bb8c: /* @__PURE__ */ __name(function(t2) {
  return t2.value;
}, "__wbg_value_692627309814bb8c"), __wbg_view_f6c15ac9fed63bbd: /* @__PURE__ */ __name(function(t2) {
  let e = t2.view;
  return c(e) ? 0 : w(e);
}, "__wbg_view_f6c15ac9fed63bbd"), __wbg_webSocket_e055969c627461a5: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    let e = t2.webSocket;
    return c(e) ? 0 : w(e);
  }, arguments);
}, "__wbg_webSocket_e055969c627461a5"), __wbg_writable_67962070d6b841eb: /* @__PURE__ */ __name(function() {
  return s(function(t2) {
    return t2.writable;
  }, arguments);
}, "__wbg_writable_67962070d6b841eb"), __wbg_write_5f693b62e780062e: /* @__PURE__ */ __name(function(t2, e) {
  return t2.write(e);
}, "__wbg_write_5f693b62e780062e"), __wbindgen_cast_2241b6af4c4b2941: /* @__PURE__ */ __name(function(t2, e) {
  return g(t2, e);
}, "__wbindgen_cast_2241b6af4c4b2941"), __wbindgen_cast_4625c577ab2ec9ee: /* @__PURE__ */ __name(function(t2) {
  return BigInt.asUintN(64, t2);
}, "__wbindgen_cast_4625c577ab2ec9ee"), __wbindgen_cast_46336c5d48bc9217: /* @__PURE__ */ __name(function(t2, e) {
  return X(t2, e, _.wasm_bindgen_27cce28d972db99d___closure__destroy___dyn_core_9b3796e30d99ddb7___ops__function__FnMut__wasm_bindgen_27cce28d972db99d___JsValue____Output_______, Y);
}, "__wbindgen_cast_46336c5d48bc9217"), __wbindgen_cast_9ae0607507abb057: /* @__PURE__ */ __name(function(t2) {
  return t2;
}, "__wbindgen_cast_9ae0607507abb057"), __wbindgen_cast_d6cd19b81560fd6e: /* @__PURE__ */ __name(function(t2) {
  return t2;
}, "__wbindgen_cast_d6cd19b81560fd6e"), __wbindgen_init_externref_table: /* @__PURE__ */ __name(function() {
  let t2 = _.__wbindgen_externrefs, e = t2.grow(4);
  t2.set(0, void 0), t2.set(e + 0, void 0), t2.set(e + 1, null), t2.set(e + 2, true), t2.set(e + 3, false);
}, "__wbindgen_init_externref_table") } };
var it = new WebAssembly.Instance(B, $);
_ = it.exports;
_.__wbindgen_start();
Error.stackTraceLimit = 100;
var A = false;
function G() {
}
__name(G, "G");
G();
var z = 0;
function U() {
  A && (console.log("Reinitializing Wasm application"), H(), A = false, G(), z++);
}
__name(U, "U");
addEventListener("error", (t2) => {
  C(t2.error);
});
function C(t2) {
  t2 instanceof WebAssembly.RuntimeError && (console.error("Critical", t2), A = true);
}
__name(C, "C");
var O = class extends st {
  static {
    __name(this, "O");
  }
};
O.prototype.fetch = function(e) {
  return J.call(this, e, this.env, this.ctx);
};
var ct = { set: /* @__PURE__ */ __name((t2, e, n, r) => Reflect.set(t2.instance, e, n, r), "set"), has: /* @__PURE__ */ __name((t2, e) => Reflect.has(t2.instance, e), "has"), deleteProperty: /* @__PURE__ */ __name((t2, e) => Reflect.deleteProperty(t2.instance, e), "deleteProperty"), apply: /* @__PURE__ */ __name((t2, e, n) => Reflect.apply(t2.instance, e, n), "apply"), construct: /* @__PURE__ */ __name((t2, e, n) => Reflect.construct(t2.instance, e, n), "construct"), getPrototypeOf: /* @__PURE__ */ __name((t2) => Reflect.getPrototypeOf(t2.instance), "getPrototypeOf"), setPrototypeOf: /* @__PURE__ */ __name((t2, e) => Reflect.setPrototypeOf(t2.instance, e), "setPrototypeOf"), isExtensible: /* @__PURE__ */ __name((t2) => Reflect.isExtensible(t2.instance), "isExtensible"), preventExtensions: /* @__PURE__ */ __name((t2) => Reflect.preventExtensions(t2.instance), "preventExtensions"), getOwnPropertyDescriptor: /* @__PURE__ */ __name((t2, e) => Reflect.getOwnPropertyDescriptor(t2.instance, e), "getOwnPropertyDescriptor"), defineProperty: /* @__PURE__ */ __name((t2, e, n) => Reflect.defineProperty(t2.instance, e, n), "defineProperty"), ownKeys: /* @__PURE__ */ __name((t2) => Reflect.ownKeys(t2.instance), "ownKeys") };
var m = { construct(t2, e, n) {
  try {
    U();
    let r = { instance: Reflect.construct(t2, e, n), instanceId: z, ctor: t2, args: e, newTarget: n };
    return new Proxy(r, { ...ct, get(o, b, u) {
      o.instanceId !== z && (o.instance = Reflect.construct(o.ctor, o.args, o.newTarget), o.instanceId = z);
      let a = Reflect.get(o.instance, b, u);
      return typeof a != "function" ? a : a.constructor === Function ? new Proxy(a, { apply(l, L, M) {
        U();
        try {
          return l.apply(L, M);
        } catch (S) {
          throw C(S), S;
        }
      } }) : new Proxy(a, { async apply(l, L, M) {
        U();
        try {
          return await l.apply(L, M);
        } catch (S) {
          throw C(S), S;
        }
      } });
    } });
  } catch (r) {
    throw A = true, r;
  }
} };
var gt = new Proxy(O, m);
var wt = new Proxy(x, m);
var lt = new Proxy(R, m);
var pt = new Proxy(I, m);
var yt = new Proxy(v, m);
var ht = new Proxy(h, m);
var mt = new Proxy(E, m);
export {
  wt as ChatState,
  lt as IntoUnderlyingByteSource,
  pt as IntoUnderlyingSink,
  yt as IntoUnderlyingSource,
  ht as MinifyConfig,
  mt as R2Range,
  gt as default
};
//# sourceMappingURL=shim.js.map
