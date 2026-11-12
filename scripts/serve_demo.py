#!/usr/bin/env python3
"""
Live prototype: English in, Hinglish out, scored, with the audience choosing the input.

This is ISA demonstration row 5, which Template 7 calls "the heaviest single row in
this component", and the same template says: *if any part of it is mocked, say so
before you run it*. So, stated here and on the page itself:

  * Nothing is mocked. Every word on screen is generated at request time by a model
    loaded from disk. There is no cache, no canned answer, no fallback string.
  * It is NOT cloud-deployed. It runs on the presenting machine and serves to
    localhost. Issue 298-56 (deploy a thin slice to the cloud) is still open, and
    this does not close it.
  * The adapter served is the MLX laptop run, `m2_qwen7b_seed42_it500`, because that
    is the adapter on this disk. The reported M2 result is the A100 NF4 three-seed
    run, which scores differently (chrF++ 51.683 against this one's 57.808) and
    code-switches considerably more. The page says so. Do not quote a number from
    this demo as the project's M2 result.

What the audience sees, for a sentence they choose:

  M1, the untrained base model, and M2, the fine-tuned adapter, on the same input,
  side by side, with CMI and switch-point fraction measured on each output by the
  same tagger `scripts/score_codemixing.py` uses. The interesting demo is not that
  M2 produces Hinglish; it is that M1 frequently does not, and that the code-mixing
  numbers move in the direction of the human references.

Usage
-----
  python scripts/serve_demo.py                 # M1 and M2, port 8000
  python scripts/serve_demo.py --no-m1         # M2 only, about half the memory
  python scripts/serve_demo.py --port 8080

M1 is loaded lazily on the first request that needs it, so startup stays quick.
Both models at 4-bit are roughly 8.4 GB of weights together; on a 16 GB machine
close the other heavy applications first, or pass --no-m1.
"""

import argparse
import json
import pathlib
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

BASE_MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"
ADAPTER = REPO_ROOT / "models/adapters/m2_qwen7b_seed42_it500"

# The prompt is read from the supervision manifest rather than retyped, so the demo
# cannot drift from what the model was trained against. data/sft/hinge/manifest.json
# records it; if that file is absent the demo refuses to start rather than guess,
# because a different prompt is a different measurement.
MANIFEST = REPO_ROOT / "data/sft/hinge/manifest.json"


def load_prompt():
    if not MANIFEST.exists():
        raise SystemExit(
            "{} is missing, so the exact training prompt is unknown.\n"
            "Run: python scripts/build_sft_data.py".format(MANIFEST))
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return m["system_prompt"], m["user_template"]


class Models:
    """Lazily-loaded MLX models. Guarded, because the server is threaded."""

    def __init__(self, want_m1):
        self.want_m1 = want_m1
        self.lock = threading.Lock()
        self.m2 = None
        self.m1 = None

    def _load(self, adapter):
        from mlx_lm import load
        kw = {"adapter_path": str(adapter)} if adapter else {}
        return load(BASE_MODEL, **kw)

    def get(self, which):
        with self.lock:
            if which == "m2":
                if self.m2 is None:
                    self.m2 = self._load(ADAPTER)
                return self.m2
            if self.m1 is None:
                self.m1 = self._load(None)
            return self.m1


def generate_one(models, which, english, system, user_tpl, max_tokens=96):
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler
    model, tok = models.get(which)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user_tpl.format(english=english)}]
    prompt = tok.apply_chat_template(messages, add_generation_prompt=True)
    t0 = time.time()
    out = generate(model, tok, prompt=prompt, max_tokens=max_tokens,
                   sampler=make_sampler(temp=0.0), verbose=False)
    # Greedy decoding, so this is reproducible: the same input gives the same output
    # every time, which matters if an audience member asks you to run it twice.
    line = next((l.strip() for l in out.strip().splitlines() if l.strip()), "")
    return line, round(time.time() - t0, 2)


def score_one(hinglish, english, markers):
    """CMI and switch-point fraction for a single sentence, same tagger as the report.

    Coverage is reported alongside them, and it is not decoration. The tagger is
    lexicon-driven: a token counts as Hindi only if it is in the 323-entry spelling
    lexicon, and as English only if it appears in the source. A Hindi word in
    neither is tagged `other` and does not enter CMI at all.

    So `I was waiting for the bus but it never aaya.` scores CMI 0.0, because
    `aaya` is not in the lexicon. That is a true statement about the measurement
    and a false one about the sentence. Live, in front of an audience choosing
    arbitrary inputs, this will happen; the page shows coverage so the gap is
    visible rather than silently wrong. It is also the reason
    `reports/m1_m2_comparison.md` reports tagger coverage beside every CMI.
    """
    from lrcs.analysis.codemixing import LANG_TAGS, cmi, spf
    from lrcs.data.clean import tag_tokens
    tagged = tag_tokens(hinglish, english, markers)
    tags = [t for _, t in tagged]
    words = [t for t in tags if t != "punct"]
    resolved = [t for t in tags if t in LANG_TAGS]
    s = spf(tags)
    return {"cmi": round(cmi(tags), 2),
            "spf": None if s is None else round(s, 4),
            "coverage": round(len(resolved) / len(words), 2) if words else None,
            "unresolved": len(words) - len(resolved),
            "devanagari": any("ऀ" <= ch <= "ॿ" for ch in hinglish)}


PAGE = """<!doctype html>
<meta charset="utf-8"><title>Hinglish prototype</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 :root{--bg:#fbfbfd;--fg:#16161a;--mut:#5a5a66;--line:#e2e2e8;--card:#fff;--acc:#2a5db0}
 @media(prefers-color-scheme:dark){:root{--bg:#131317;--fg:#ececf0;--mut:#a0a0ad;
   --line:#2c2c34;--card:#1c1c22;--acc:#7aa6ef}}
 *{box-sizing:border-box}
 body{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);
   font:16px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
 .wrap{max-width:860px;margin:0 auto}
 h1{font-size:1.5rem;margin:0 0 4px}
 .sub{color:var(--mut);font-size:.92rem;margin-bottom:18px}
 .note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--acc);
   border-radius:8px;padding:12px 14px;font-size:.86rem;color:var(--mut);margin-bottom:18px}
 textarea{width:100%;min-height:76px;padding:12px;font:inherit;border-radius:8px;
   border:1px solid var(--line);background:var(--card);color:var(--fg);resize:vertical}
 button{margin-top:10px;padding:10px 20px;font:inherit;font-weight:600;border:0;
   border-radius:8px;background:var(--acc);color:#fff;cursor:pointer}
 button:disabled{opacity:.5;cursor:default}
 .cards{display:grid;gap:14px;margin-top:22px}
 @media(min-width:680px){.cards{grid-template-columns:1fr 1fr}}
 .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
 .card h2{font-size:.78rem;letter-spacing:.07em;text-transform:uppercase;
   color:var(--mut);margin:0 0 8px}
 .out{font-size:1.06rem;min-height:2.6em}
 .met{margin-top:10px;padding-top:9px;border-top:1px solid var(--line);
   font-size:.82rem;color:var(--mut);font-variant-numeric:tabular-nums}
 .warn{color:#c2410c;font-weight:600}
 @media(prefers-color-scheme:dark){.warn{color:#fb923c}}
 .ex{margin-top:10px;font-size:.84rem;color:var(--mut)}
 .ex a{color:var(--acc);cursor:pointer;margin-right:12px;text-decoration:underline}
 footer{margin-top:26px;font-size:.8rem;color:var(--mut);border-top:1px solid var(--line);
   padding-top:12px}
</style>
<div class="wrap">
<h1>English &rarr; Hinglish</h1>
<div class="sub">Model 1 (no training) against Model 2 (QLoRA fine-tune), same base model,
your sentence.</div>

<div class="note">
<b>Nothing here is mocked.</b> Each output is generated when you press the button, greedy
decoding, no cache &mdash; run the same sentence twice and it will match.
<b>This is not cloud-deployed:</b> it runs on the presenting laptop (Linear 298-56 is still open).
The adapter served is the MLX laptop run; the project's reported M2 is the A100 NF4 three-seed
run, which scores lower on chrF++ and code-switches more.
</div>

<textarea id="t" placeholder="Type an English sentence…">The weather is very nice today.</textarea>
<div class="ex">Try:
 <a onclick="ex('Please submit your assignment before Friday.')">an instruction</a>
 <a onclick="ex('I was waiting for the bus but it never came.')">a narrative</a>
 <a onclick="ex('Install the standard and TSC pumps.')">a technical one</a>
</div>
<button id="b" onclick="go()">Translate</button>

<div class="cards">
 <div class="card"><h2>M1 &mdash; zero-shot, untrained</h2>
   <div class="out" id="o1">&mdash;</div><div class="met" id="m1">&nbsp;</div></div>
 <div class="card"><h2>M2 &mdash; QLoRA fine-tuned</h2>
   <div class="out" id="o2">&mdash;</div><div class="met" id="m2">&nbsp;</div></div>
</div>

<footer>CMI = Code-Mixing Index, SPF = switch-point fraction, measured by the same tagger as
<code>scripts/score_codemixing.py</code>. Human references on the HinGE test set average
<b>CMI 25.86</b>, <b>SPF 0.237</b>. English scores 0 on both by definition.</footer>
</div>
<script>
function ex(s){document.getElementById('t').value=s;go();}
function fmt(m){
  if(!m) return '&nbsp;';
  let s='CMI '+m.cmi+' &middot; SPF '+(m.spf===null?'n/a':m.spf)+' &middot; '+m.secs+'s';
  if(m.unresolved>0){
    // Say it on screen rather than let a wrong-looking CMI stand unexplained.
    s+='<br><span class="warn">'+m.unresolved+' word'+(m.unresolved>1?'s':'')+
       ' not in the tagger lexicon (coverage '+m.coverage+'), so CMI understates this one</span>';
  }
  if(m.devanagari) s+=' &middot; <span class="warn">Devanagari leaked</span>';
  return s;
}
async function go(){
  const t=document.getElementById('t').value.trim(); if(!t) return;
  const b=document.getElementById('b'); b.disabled=true; b.textContent='Generating…';
  for(const i of ['o1','o2']){document.getElementById(i).textContent='…';}
  document.getElementById('m1').innerHTML='&nbsp;';
  document.getElementById('m2').innerHTML='&nbsp;';
  try{
    const r=await fetch('/translate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:t})});
    const d=await r.json();
    if(d.error){document.getElementById('o2').textContent='Error: '+d.error;}
    else{
      document.getElementById('o1').textContent=d.m1?d.m1.text:'(M1 not loaded; --no-m1)';
      document.getElementById('o2').textContent=d.m2.text;
      document.getElementById('m1').innerHTML=fmt(d.m1);
      document.getElementById('m2').innerHTML=fmt(d.m2);
    }
  }catch(e){document.getElementById('o2').textContent='Request failed: '+e;}
  b.disabled=false; b.textContent='Translate';
}
</script>
"""


def make_handler(models, system, user_tpl, markers, want_m1):

    class Handler(BaseHTTPRequestHandler):

        def log_message(self, fmt, *a):      # one tidy line per request
            sys.stderr.write("  %s\n" % (fmt % a))

        def _send(self, code, body, ctype):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE, "text/html; charset=utf-8")
            else:
                self._send(404, "not found", "text/plain")

        def do_POST(self):
            if self.path != "/translate":
                return self._send(404, "not found", "text/plain")
            n = int(self.headers.get("Content-Length") or 0)
            try:
                text = (json.loads(self.rfile.read(n))["text"] or "").strip()
            except Exception as exc:
                return self._send(400, json.dumps({"error": str(exc)}), "application/json")
            if not text:
                return self._send(400, json.dumps({"error": "empty input"}),
                                  "application/json")
            out = {}
            try:
                for which in (("m1", "m2") if want_m1 else ("m2",)):
                    line, secs = generate_one(models, which, text, system, user_tpl)
                    out[which] = dict(score_one(line, text, markers), text=line, secs=secs)
            except Exception as exc:
                # Surfaced to the page rather than only the console: during a live demo
                # nobody is reading the terminal.
                return self._send(500, json.dumps({"error": repr(exc)}), "application/json")
            self._send(200, json.dumps(out), "application/json")

    return Handler


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-m1", action="store_true",
                   help="serve only M2; roughly half the memory")
    p.add_argument("--lexicon", default=str(REPO_ROOT / "analysis/spelling_variants.tsv"))
    p.add_argument("--warm", action="store_true",
                   help="load the models before serving, so the first demo request is fast")
    args = p.parse_args(argv)

    if not ADAPTER.exists():
        raise SystemExit("adapter not found: {}\nTrain it, or pass a different path."
                         .format(ADAPTER))

    from lrcs.data.clean import hindi_markers
    from lrcs.lexicon import load_variant_groups
    markers = hindi_markers(load_variant_groups(args.lexicon))
    system, user_tpl = load_prompt()

    models = Models(want_m1=not args.no_m1)
    if args.warm:
        print("loading M2 …", flush=True)
        models.get("m2")
        if not args.no_m1:
            print("loading M1 …", flush=True)
            models.get("m1")

    handler = make_handler(models, system, user_tpl, markers, want_m1=not args.no_m1)
    srv = HTTPServer(("127.0.0.1", args.port), handler)
    print("\n  Hinglish prototype on http://127.0.0.1:{}".format(args.port))
    print("  M1 {} | adapter {}".format(
        "off (--no-m1)" if args.no_m1 else "on", ADAPTER.relative_to(REPO_ROOT)))
    print("  Not cloud-deployed; 298-56 remains open. Ctrl-C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
