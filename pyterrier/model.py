import pandas as pd

# This file has useful methods for using the Pyterrier Pandas datamodel

# the first rank SHOULD be 0, see the standard "Welcome to TREC email"
FIRST_RANK = 0

# Standard data types that transformers provide and require
QUERIES = ["qid", "query"]
DOCS = ["docno"]
RANKED_DOCS = ["qid", "query", "docno", "score", "rank"]
DOCS_FEATURES = ["docno", "features"]
RANKED_DOCS_FEATURES = ["qid", "docno", "score", "rank", "features"]


# set to True to ensure that the resulting dataframe is correctly /ordered/
# as well as having correct ranks assigned
STRICT_SORT = False

def add_ranks(rtr):
    rtr.drop(columns=["rank"], errors="ignore", inplace=True)
    if len(rtr) == 0:
        rtr["rank"] = pd.Series(index=rtr.index, dtype='int64')
        return rtr

    # -1 assures that first rank will be FIRST_RANK
    rtr["rank"] = rtr.groupby("qid", sort=False).rank(ascending=False, method="first")["score"].astype(int) -1 + FIRST_RANK
    if STRICT_SORT:
        rtr.sort_values(["qid", "rank"], ascending=[True,True], inplace=True )
    return rtr
    
def coerce_queries_dataframe(query):
    """
    Convert either a string or a list of strings to a dataframe for use as topics in retrieval.

    Args:
        query: Either a string or a list of strings

    Returns:
        dataframe with columns=['qid','query']
    """
    if isinstance(query, pd.DataFrame):
        return query
    elif isinstance(query, str):
        return pd.DataFrame([["1", query]], columns=['qid', 'query'])
    # if queries is a list or tuple
    elif isinstance(query, list) or isinstance(query, tuple):
        # if the list or tuple is made of strings
        if query != [] and isinstance(query[0], str):
            indexed_query = []
            for i, item in enumerate(query):
                # all elements must be of same type
                assert isinstance(item, str), f"{item} is not a string"
                indexed_query.append([str(i + 1), item])
            return pd.DataFrame(indexed_query, columns=['qid', 'query'])
    # catch-all when we dont recognise the type
    raise ValueError("Could not coerce %s (type %s) into a DataFrame of queries" % (str(query), str(type(query))))


# def check_types(beforet, aftert, input, transformer_type="base"):
#     # does the output of beforet, given the input, fit into aftert
#     # if fail then say why
#     # i.e. output of beforet is x given input, but aftert requires y
#     # if beforet not binarytransformer or narytransformer just try/catch .validate to check fields
#     if transformer_type == "binary":
#         # first validate sub components
#         try:
#             beforet.validate(input)
#         except TypeError:
#             raise TypeError(generate_type_error(beforet, input))
#
#         try:
#             aftert.validate(input)
#         except TypeError:
#             raise TypeError(generate_type_error(aftert, input))
#
#         # then validate yourself with
#     pass