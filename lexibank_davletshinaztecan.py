import attr
from pathlib import Path
from clldutils.misc import slug
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank import Concept, Language, FormSpec
from lingpy import *
from pylexibank import progressbar

import re


@attr.s
class CustomConcept(Concept):
    ProtoAztecan = attr.ib(default=None)
    Number = attr.ib(default=None)


@attr.s
class CustomLanguage(Language):
    Source = attr.ib(default=None)
    Location = attr.ib(default=None)


class Dataset(BaseDataset):
    id = "davletshinaztecan"
    dir = Path(__file__).parent
    concept_class = CustomConcept
    language_class = CustomLanguage
    form_spec = FormSpec(
        missing_data=["*", "---", "-"],
        separators=";/,~",
        strip_inside_brackets=True,
        brackets={"(": ")"},
        first_form_only=True,
    )

    def cmd_makecldf(self, args):
        # Add bibliographic sources and collect them
        args.writer.add_sources()
        sources = {}
        for language in self.languages:
            sources[language["ID"]] = language["Source"]
            args.writer.add_language(**language)

        # Add concepts and collecte them
        concepts, proto = {}, {}
        for concept in self.conceptlists[0].concepts.values():
            idx = "{0}_{1}".format(concept.number, slug(concept.english))
            args.writer.add_concept(
                ID=idx,
                Name=concept.english,
                ProtoAztecan=concept.attributes["proto_aztecan"],
                Number=concept.number,
                Concepticon_ID=concept.concepticon_id,
                Concepticon_Gloss=concept.concepticon_gloss,
            )
            concepts[concept.number] = idx
            proto[concept.number] = concept.attributes['proto_aztecan']

        cogidx = 0
        with open(self.raw_dir.joinpath("data.txt").as_posix()) as f:
            for line in progressbar(f, desc="cldfify"):
                number, concept = line.split(" :: ")[0].split(". ")
                entries = re.split(
                    r"(\(-*[0-9]\))[,\.]*", line.split(" :: ")[1]
                )
                cogids = []
                for i in range(0, len(entries) - 1, 2):
                    entry = entries[i].strip()
                    cogid = int(entries[i + 1][1:-1])
                    language = entry.split(" ")[0]
                    value = " ".join(entry.split(" ")[1:])
                    for lex in args.writer.add_forms_from_value(
                        Language_ID=language,
                        Parameter_ID=concepts[number],
                        Value=value,
                        Source=[sources[language]],
                    ):
                        args.writer.add_cognate(
                            lexeme=lex,
                            Cognateset_ID=cogid + cogidx,
                            Source="Davletshin2012",
                        )
                    cogids += [cogid]

                # add proto-aztecan form
                if proto[number].strip() != "?":
                    for lex in args.writer.add_forms_from_value(
                        Language_ID="PA",
                        Parameter_ID=concepts[number],
                        Value=proto[number],
                        Source=sources["PA"],
                    ):
                        args.writer.add_cognate(
                            lexeme=lex,
                            Cognateset_ID=sorted(
                                cogids,
                                key=lambda x: cogids.count(x),
                                reverse=True,
                            )[0]
                            + cogidx,
                        )

                cogidx += max(cogids)
