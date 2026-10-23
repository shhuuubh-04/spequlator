import { type ReactNode, useState } from "react";
import { FINDING_LABEL, TEXT_LABEL, num } from "../format";
import type { Explained, TokenStep } from "../types";
import { Ticks } from "./Marked";

const ROW_PREVIEW = 8;
const SET_LIMIT = 40;

function SetOf({ items }: { items: string[] }) {
  if (items.length === 0) return <span className="muted">none</span>;
  const shown = items.slice(0, SET_LIMIT);
  return (
    <code className="set">
      {"{"}
      {shown.join(", ")}
      {items.length > SET_LIMIT ? `, … ${items.length - SET_LIMIT} more` : ""}
      {"}"}
    </code>
  );
}

function Step({ title, lead, children }: { title: string; lead: string; children: ReactNode }) {
  return (
    <li className="step">
      <h3>{title}</h3>
      <p className="lead">{lead}</p>
      {children}
    </li>
  );
}

function Result({ children }: { children: ReactNode }) {
  return <p className="result">{children}</p>;
}

function Tokens({ step }: { step: TokenStep }) {
  return (
    <div className="tokens">
      <p>
        {step.label}: {step.n_tokens} tokens, {step.n_vocab} of them in the vocabulary.
      </p>
      <p className="token-row">
        {step.tokens.map((t, i) => (
          <span key={i} className={t.vocab ? "tok" : "tok oov"}>
            {t.t}
          </span>
        ))}
        {step.more > 0 && <span className="muted"> … {step.more} more</span>}
      </p>
    </div>
  );
}

function TfidfTable({ data }: { data: Explained }) {
  const [all, setAll] = useState(false);
  const t = data.trace.tfidf;
  const others = Object.keys(t.cos);
  return (
    <>
      <div className="table-scroll">
        <table className="worked">
          <thead>
            <tr>
              <th scope="col">Term</th>
              <th scope="col" className="num">Count</th>
              <th scope="col" className="num">tf</th>
              <th scope="col" className="num">df</th>
              <th scope="col" className="num">idf</th>
              <th scope="col" className="num">Weight</th>
              <th scope="col" className="num">Unit, doc</th>
              {others.map((o) => (
                <th key={`u${o}`} scope="col" className="num">
                  Unit, {TEXT_LABEL[o]}
                </th>
              ))}
              {others.map((o) => (
                <th key={`c${o}`} scope="col" className="num">
                  doc × {TEXT_LABEL[o]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {t.rows.map((r, i) => (
              <tr key={r.term} className={i >= ROW_PREVIEW && !all ? "extra" : ""}>
                <th scope="row">
                  <code>{r.term}</code>
                </th>
                <td className="num">{r.count.doc}</td>
                <td className="num">{num(r.tf.doc, 3)}</td>
                <td className="num">{r.df}</td>
                <td className="num">{num(r.idf, 3)}</td>
                <td className="num">{num(r.weight.doc, 3)}</td>
                <td className="num">{num(r.unit.doc, 4)}</td>
                {others.map((o) => (
                  <td key={`u${o}`} className="num">
                    {num(r.unit[o], 4)}
                  </td>
                ))}
                {others.map((o) => (
                  <td key={`c${o}`} className="num">
                    {num(r.contrib[o], 4)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={7 + others.length}>
                Sum over all {t.rows.length} terms = cosine
              </th>
              {others.map((o) => (
                <td key={o} className="num" data-testid={`cos-${o}`}>
                  {num(t.cos[o], 4)}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
      {t.rows.length > ROW_PREVIEW && (
        <button type="button" className="text-button no-print" onClick={() => setAll((a) => !a)}>
          {all ? "Show the top terms only" : `Show all ${t.rows.length} terms`}
        </button>
      )}
    </>
  );
}

export function Method({ data }: { data: Explained }) {
  const { trace } = data;
  const change = trace.mode === "change";
  const t = trace.tfidf;
  const e = trace.encoder;
  const c = trace.combine;
  const r1 = trace.r1;
  const r2 = trace.r2;
  const [docTokens, ...codeTokens] = trace.tokens;
  const removed = trace.diff?.filter((l) => l.sign === "-").length ?? 0;
  const added = trace.diff?.filter((l) => l.sign === "+").length ?? 0;

  return (
    <ol className="method">
      <Step title="Read the inputs" lead="The texts are taken exactly as given; nothing is sent off this machine.">
        <div className="table-scroll">
        <table className="worked compact">
          <thead>
            <tr>
              <th scope="col">Text</th>
              <th scope="col" className="num">Characters</th>
              <th scope="col" className="num">Words</th>
              <th scope="col" className="num">Lines</th>
            </tr>
          </thead>
          <tbody>
            {trace.inputs.map((s) => (
              <tr key={s.key}>
                <th scope="row">{s.label}</th>
                <td className="num">{s.chars}</td>
                <td className="num">{s.words}</td>
                <td className="num">{s.lines}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </Step>

      <Step
        title="Find what changed"
        lead={
          change
            ? "The two code versions are compared line by line with Python's difflib, the same format CoDocBench uses."
            : "Snapshot mode has no earlier version, so there is no diff and rule R2 cannot run."
        }
      >
        {change && (
          <Result>
            {removed} lines removed and {added} added. They are shown under Evidence.
          </Result>
        )}
      </Step>

      <Step
        title="Split the text into tokens"
        lead="Identifiers are broken at underscores and case changes, everything is lower-cased, and single letters and punctuation are dropped."
      >
        {docTokens.splits.length > 0 && (
          <ul className="splits">
            {docTokens.splits.map(([ident, parts]) => (
              <li key={ident}>
                <code>{ident}</code> becomes {parts.map((p) => <code key={p} className="part">{p}</code>)}
              </li>
            ))}
          </ul>
        )}
        <Tokens step={docTokens} />
        <details className="code-tokens">
          <summary>Tokens of the code</summary>
          {codeTokens.map((s) => (
            <Tokens key={s.key} step={s} />
          ))}
        </details>
        <p className="caption">Grey, struck-through tokens are not in the vocabulary learned from the training data, so TF-IDF ignores them.</p>
      </Step>

      <Step
        title="Rule R1: compare the parameters"
        lead="The code's signature is parsed with Python's ast module and the docstring's parameter list with docstring_parser; then the two sets are compared."
      >
        <dl className="sets">
          <dt>Parameters in the signature</dt>
          <dd>
            <SetOf items={r1.signature} />
            {r1.def_line && <code className="def-line">{r1.def_line}</code>}
          </dd>
          <dt>Parameters in the docstring</dt>
          <dd>
            <SetOf items={r1.documented} />
          </dd>
          <dt>Docstring minus signature</dt>
          <dd>
            <SetOf items={r1.stale} />
          </dd>
          <dt>Signature minus docstring</dt>
          <dd>
            <SetOf items={r1.undocumented} /> <span className="muted">Shown for information; R1 does not use this direction.</span>
          </dd>
        </dl>
        <Result>
          {!r1.applicable
            ? "Not applicable: no signature was found, or the docstring lists no parameters."
            : r1.fired
              ? "R1 fires: the docstring describes parameters the code does not have."
              : r1.stale.length && r1.has_kwargs
                ? "R1 does not fire: the function takes **kwargs, so the extra names may be valid."
                : "R1 does not fire: every documented parameter is in the signature."}
        </Result>
      </Step>

      <Step
        title="Rule R2: words only the removed lines had"
        lead="Content words are tokens of three or more letters that are not common English or Python words."
      >
        {r2 ? (
          <>
            <dl className="sets">
              <dt>Content words in the removed lines</dt>
              <dd>
                <SetOf items={r2.removed} />
              </dd>
              <dt>Minus those still in the new code</dt>
              <dd>
                <SetOf items={r2.still_present} />
              </dd>
              <dt>Gone from the code</dt>
              <dd>
                <SetOf items={r2.gone} />
              </dd>
              <dt>Gone and mentioned in the documentation</dt>
              <dd>
                <SetOf items={r2.hits} />
              </dd>
            </dl>
            <Result>
              {!r2.applicable
                ? "Not applicable: the change removes no lines."
                : r2.fired
                  ? `R2 fires on ${r2.hits.length} word${r2.hits.length === 1 ? "" : "s"}. Whether that decides the finding depends on the combined score (step 9).`
                  : "R2 does not fire."}
            </Result>
          </>
        ) : (
          <Result>Not used in snapshot mode.</Result>
        )}
      </Step>

      <Step
        title="Weigh the words with TF-IDF"
        lead={`Rare words count for more than common ones. The vocabulary has ${t.vocab_size.toLocaleString("en")} terms, learned from ${t.n_train_texts.toLocaleString("en")} training texts (terms seen in at least ${t.min_df}).`}
      >
        <ul className="formulas">
          <li>tf = 1 + ln(count)</li>
          <li>
            idf = ln((1 + n) ÷ (1 + df)) + 1, where n = {t.n_train_texts.toLocaleString("en")} and df is the number of training texts containing the term
          </li>
          <li>weight = tf × idf</li>
          <li>unit weight = weight ÷ ‖v‖, where ‖v‖ = √(sum of every weight² in that text)</li>
          <li>cosine = sum over shared terms of (unit weight in the documentation × unit weight in the code)</li>
        </ul>
        <div className="table-scroll">
        <table className="worked compact">
          <thead>
            <tr>
              <th scope="col">Text</th>
              <th scope="col" className="num">Terms</th>
              <th scope="col" className="num">Tokens ignored</th>
              <th scope="col" className="num">Sum of weight²</th>
              <th scope="col" className="num">‖v‖</th>
            </tr>
          </thead>
          <tbody>
            {t.vectors.map((v) => (
              <tr key={v.key}>
                <th scope="row">{v.label}</th>
                <td className="num">{v.n_terms}</td>
                <td className="num">{v.out_of_vocab}</td>
                <td className="num">{num(v.sum_sq, 3)}</td>
                <td className="num">{num(v.norm, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        <TfidfTable data={data} />
        <Result>
          {change
            ? `cos(doc, new) − cos(doc, old) = ${num(t.cos.new, 4)} − ${num(t.cos.old, 4)} = ${num(t.delta, 4, true)}`
            : `cos(doc, code) = ${num(t.cos.code, 4)}`}
        </Result>
      </Step>

      <Step
        title="Compare the meaning with the encoder"
        lead="A small transformer turns each text into a list of numbers so that texts with similar meaning point in similar directions."
      >
        {e.status !== "ok" ? (
          <Result>
            {e.status === "off"
              ? "Not computed: the encoder is switched off, so only TF-IDF and the rules were used."
              : "Not computed: the encoder could not run, so only TF-IDF and the rules were used."}
          </Result>
        ) : (
          <>
            <p>
              Model: {e.model}. Each text becomes {e.dim} numbers of total length 1.
              {e.max_seq_length ? ` Texts longer than ${e.max_seq_length} sub-word tokens are cut.` : ""} The trace shows what goes in
              and comes out of the network, not its internal layers.
            </p>
            <div className="table-scroll">
              <table className="worked compact">
                <thead>
                  <tr>
                    <th scope="col">Text</th>
                    <th scope="col" className="num">Sub-word tokens</th>
                    <th scope="col">Cut?</th>
                    <th scope="col">First dimensions</th>
                    <th scope="col" className="num">Length</th>
                  </tr>
                </thead>
                <tbody>
                  {e.texts.map((x) => (
                    <tr key={x.key}>
                      <th scope="row">{x.label}</th>
                      <td className="num">{x.n_tokens ?? "n/a"}</td>
                      <td>{x.truncated ? "Yes" : "No"}</td>
                      <td>
                        <code className="vec">[{x.head.map((v) => num(v, 3)).join(", ")}, …]</code>
                      </td>
                      <td className="num">{num(x.norm, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {e.texts[0]?.pieces.length > 0 && (
              <p className="token-row">
                {e.texts[0].pieces.map((p, i) => (
                  <span key={i} className="tok">
                    {p}
                  </span>
                ))}
                <span className="muted"> first sub-word tokens of the documentation</span>
              </p>
            )}
            <ul className="formulas">
              {Object.keys(e.cos).map((o) => (
                <li key={o}>
                  cos(doc, {o}) = {e.products[o].map((p) => num(p, 4)).join(" + ")} + … ({e.dim} products) = {num(e.cos[o], 4)}
                </li>
              ))}
            </ul>
            {e.delta !== null && (
              <Result>
                cos(doc, new) − cos(doc, old) = {num(e.cos.new, 4)} − {num(e.cos.old, 4)} = {num(e.delta, 4, true)}
              </Result>
            )}
          </>
        )}
      </Step>

      <Step
        title="Combine the two signals"
        lead="Each change is divided by its usual spread on the training data, so word overlap and meaning count equally."
      >
        {c ? (
          <>
            <p className="formula">
              {c.encoder !== null ? (
                <>
                  z = ({num(c.tfidf, 4)} ÷ {num(c.scale_tfidf, 4)} + {num(c.encoder, 4)} ÷ {num(c.scale_encoder, 4)}) ÷ 2 = (
                  {num(c.parts[0], 3)} + {num(c.parts[1], 3)}) ÷ 2 = <strong>{num(c.z, 3, true)}</strong>
                </>
              ) : (
                <>
                  z = {num(c.tfidf, 4)} ÷ {num(c.scale_tfidf, 4)} = <strong>{num(c.z, 3, true)}</strong>
                </>
              )}
            </p>
            <p className="caption">
              The spreads ({num(c.scale_tfidf, 4)} and {num(c.scale_encoder, 4)}) and the undecided band ±{num(c.eps, 4)} were set on the
              training split only and frozen before testing (decision D-028, settings {trace.constants.thresholds_version}).
            </p>
          </>
        ) : (
          <Result>Not used in snapshot mode: a single similarity score cannot show drift.</Result>
        )}
      </Step>

      <Step title="Decide" lead="The checks run in this order; the first yes decides the finding.">
        <ol className="checks">
          {trace.decision.checks.map((k) => (
            <li key={k.key} className={`check check-${k.result.replace(" ", "-")}`} aria-current={k.result === "yes" ? "step" : undefined}>
              <span className="q">{k.question}</span>
              <span className="d">{k.detail}</span>
              <span className="r">
                {k.result === "yes" ? `Yes, so: ${FINDING_LABEL[k.outcome]}` : k.result === "no" ? "No" : "Not reached"}
              </span>
            </li>
          ))}
        </ol>
      </Step>

      <Step title="Write the report" lead={`The sentences come from fixed templates; this one is "${trace.text.reason}", filled with the values above.`}>
        <blockquote className="quote">
          <p>
            <Ticks text={trace.text.summary} />
          </p>
          <p>
            Next step: <Ticks text={trace.text.next_step} />
          </p>
        </blockquote>
      </Step>
    </ol>
  );
}