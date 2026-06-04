"""Pre-configured templates for the LangExtract Studio."""

TEMPLATES = {
    "romeo_juliet": {
        "name": "Romeo & Juliet (Characters & Emotions)",
        "description": "Extract characters, their emotions, and romantic/metaphorical relationships from dramatic dialogue.",
        "prompt": "Extract characters, emotions, and relationships in order of appearance.\nUse exact text for extractions. Do not paraphrase or overlap entities.\nProvide meaningful attributes for each entity to add context.",
        "schema": {
            "character": {
                "emotional_state": "Current emotion or state of mind (e.g. wonder, sorrow)"
            },
            "emotion": {
                "feeling": "Description of the feeling captured by the expression"
            },
            "relationship": {
                "type": "The style or context of relationship described (e.g. metaphor, marriage)"
            }
        },
        "examples": [
            {
                "text": "ROMEO. But soft! What light through yonder window breaks? It is the east, and Juliet is the sun.",
                "extractions": [
                    {
                        "extraction_class": "character",
                        "extraction_text": "ROMEO",
                        "attributes": {"emotional_state": "wonder"}
                    },
                    {
                        "extraction_class": "emotion",
                        "extraction_text": "But soft!",
                        "attributes": {"feeling": "gentle awe"}
                    },
                    {
                        "extraction_class": "relationship",
                        "extraction_text": "Juliet is the sun",
                        "attributes": {"type": "metaphor"}
                    }
                ]
            }
        ],
        "input_text": "Lady Juliet gazed longingly at the stars, her heart aching for Romeo. But soft! She whispered, \"My love is as deep as the sea.\""
    },
    "clinical_note": {
        "name": "Clinical Trial Medication & Dosage",
        "description": "Identify medical treatments, including medication names, dosages, administration routes, and dosage frequencies.",
        "prompt": "Extract medications, dosages, and frequencies from the clinical note.\nUse exact text for all extractions. Ensure attributes capture medical context accurately.",
        "schema": {
            "medication": {
                "generic_name": "Generic chemical name of the drug",
                "class": "Drug class (e.g. biguanide, beta-blocker)"
            },
            "dosage": {
                "amount": "The numeric quantity/concentration (e.g., 500mg, 10mg)",
                "route": "Administration route (e.g. oral, intravenous)"
            },
            "frequency": {
                "interval": "Standard medical shorthand or description (e.g. BID, once daily)"
            }
        },
        "examples": [
            {
                "text": "Patient was started on Metformin 500mg orally twice daily for diabetes control.",
                "extractions": [
                    {
                        "extraction_class": "medication",
                        "extraction_text": "Metformin",
                        "attributes": {"generic_name": "metformin", "class": "biguanide"}
                    },
                    {
                        "extraction_class": "dosage",
                        "extraction_text": "500mg",
                        "attributes": {"amount": "500mg", "route": "oral"}
                    },
                    {
                        "extraction_class": "frequency",
                        "extraction_text": "twice daily",
                        "attributes": {"interval": "twice daily"}
                    }
                ]
            }
        ],
        "input_text": "DISCHARGE SUMMARY:\nHe was prescribed Lisinopril 10mg once daily for hypertension. For pain, take Acetaminophen 325mg as needed every 6 hours."
    },
    "recipes": {
        "name": "Recipe Ingredients & Methods",
        "description": "Parse recipes into ingredient components, specific volumes/weights, and procedural cooking instructions.",
        "prompt": "Extract ingredients, quantities, and preparation steps from the recipe text.\nEnsure text matches verbatim and attributes describe culinary units and details.",
        "schema": {
            "ingredient": {
                "name": "Ingredient standard name",
                "state": "State of preparation (e.g., chopped, melted, sifted)"
            },
            "quantity": {
                "amount": "Numeric amount",
                "unit": "Measurement unit (e.g. cups, grams, tbsp)"
            },
            "step": {
                "action": "Core culinary action verb"
            }
        },
        "examples": [
            {
                "text": "Add 2 cups of chopped onions to the pan and saute until translucent.",
                "extractions": [
                    {
                        "extraction_class": "ingredient",
                        "extraction_text": "onions",
                        "attributes": {"name": "onion", "state": "chopped"}
                    },
                    {
                        "extraction_class": "quantity",
                        "extraction_text": "2 cups",
                        "attributes": {"amount": "2", "unit": "cups"}
                    },
                    {
                        "extraction_class": "step",
                        "extraction_text": "saute until translucent",
                        "attributes": {"action": "saute"}
                    }
                ]
            }
        ],
        "input_text": "To bake the bread, combine 500g of white flour with 7g of dry yeast. Mix with 350ml of warm water, then knead for 10 minutes."
    }
}
