# 출처 근거 경쟁 질문 / Provenance evidence questions

Run these queries over `evidence-example.ttl` with `evidence-schema.ttl`. The
fixture is entirely synthetic. Its independently reviewed documents illustrate
the schema and do not attest any real asset. Project evidence sidecars remain
isolated: actual assets reuse MV IRIs, while their claim IRIs and project IDs are
project-specific.

### EV-01. Which local files were observed or failed, and what bytes and source-copy comparisons support that result?

Expected synthetic answer: two observed local claims, one registered-copy
evidence row per asset. If bytes no longer match, a failed claim must carry a
failure reason. Neither result identifies an original model or prompt.

~~~sparql
PREFIX ev: <https://example.org/ontology/evidence#>
SELECT ?project ?asset ?status ?checked ?checker ?expected ?sourceState ?record ?file ?hash ?reason
WHERE {
    ?claim a ev:VerificationClaim ; ev:scope ev:LocalFileIntegrity ;
        ev:projectIdentifier ?project ; ev:assetIdentifier ?asset ;
        ev:status ?status ; ev:checkedAt ?checked ; ev:checkedBy ?checker ;
        ev:expectedSHA256 ?expected ; ev:sourceCopyState ?sourceState ; ev:hasEvidence ?record .
    ?record a ev:EvidenceRecord ; ev:evidenceRole "registered-copy" ; ev:evidenceURI ?file ; ev:sha256 ?hash .
    OPTIONAL { ?claim ev:unknownReason ?reason }
}
ORDER BY ?asset
~~~

### EV-02. Which original generation and origin assertions remain unverified, and why?

Expected synthetic answer: original generation and original origin for
`syntheticA`, each with its own reason, asset IRI and check metadata. Missing
claims are not counted as known unknowns. Local registration does not answer
this question.

~~~sparql
PREFIX ev: <https://example.org/ontology/evidence#>
SELECT ?asset ?target ?scope ?reason ?checked ?checker
WHERE {
    ?claim a ev:VerificationClaim ; ev:assetIdentifier ?asset ; ev:aboutAsset ?target ;
        ev:scope ?scope ; ev:status ev:Unverified ; ev:unknownReason ?reason ;
        ev:checkedAt ?checked ; ev:checkedBy ?checker .
    ?scope a ev:ClaimScope .
    ev:Unverified a ev:VerificationStatus .
    FILTER (?scope IN (ev:OriginalGeneration, ev:OriginalOrigin))
}
ORDER BY ?asset ?scope
~~~

### EV-03. Which original assertions were independently verified, against which reviewed document, and when?

Expected synthetic answer: the two original claims for `syntheticB`; only the
generation row has model and prompt, and only the origin row has an original
origin IRI. Removing reviewed evidence makes the query return no answer and
fails claim validation; a local file digest alone supplies no answer.

~~~sparql
PREFIX ev: <https://example.org/ontology/evidence#>
SELECT ?asset ?scope ?verified ?checked ?checker ?model ?prompt ?origin ?document ?hash
WHERE {
    ?claim a ev:VerificationClaim ; ev:assetIdentifier ?asset ; ev:scope ?scope ;
        ev:status ev:Verified ; ev:verifiedAt ?verified ; ev:checkedAt ?checked ;
        ev:checkedBy ?checker ; ev:hasEvidence ?record .
    ?record a ev:EvidenceRecord ; ev:evidenceRole "independently-reviewed-document" ;
        ev:evidenceURI ?document ; ev:sha256 ?hash .
    FILTER (?scope IN (ev:OriginalGeneration, ev:OriginalOrigin))
    OPTIONAL { ?claim ev:originalModel ?model }
    OPTIONAL { ?claim ev:originalPrompt ?prompt }
    OPTIONAL { ?claim ev:originalOriginIRI ?origin }
}
ORDER BY ?asset ?scope
~~~
