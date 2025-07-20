import uuid


def initiate_pylate(**config):
    from pylate import indexes, models, retrieve

    hf_model = "Alibaba-NLP/gte-modernbert-base"
    model = models.ColBERT(model_name_or_path=hf_model, document_length=8192, **config)
    print("=== Loaded model successfully ===")

    index = indexes.PLAID(
        index_folder="pylate-indexes",
        index_name="dino_repo_index",
        override=True,
        embedding_size=768,
    )
    retriever = retrieve.ColBERT(index=index)
    print("=== Created Index successfully a ===")
    return model, retriever, index


def load_data(code_5=None):
    code_1 = """
    def r(a):
        if len(a) < 2:
            return a
        i = len(a) // 2
        x = r(a[:i])
        y = r(a[i:])
        o = []
        p1 = p2 = 0
        while p1 < len(x) and p2 < len(y):
            if x[p1] <= y[p2]:
                o.append(x[p1])
                p1 += 1
            else:
                o.append(y[p2])
                p2 += 1
        o.extend(x[p1:])
        o.extend(y[p2:])
        return o
    """
    code_2 = """

    def p(a, t):
        l, h = 0, len(a) - 1
        while l <= h:
            m = (l + h) // 2
            if a[m] == t:
                return m
            if a[m] < t:
                l = m + 1
            else:
                h = m - 1
        return -1
    """

    code_3 = """
        def q(a):
            if len(a) < 2:
                return a
            pvt = a[len(a) // 2]
            l = [x for x in a if x < pvt]
            e = [x for x in a if x == pvt]
            g = [x for x in a if x > pvt]
            return q(l) + e + q(g)
    """

    code_4 = """

        from collections import deque

        def s(g, start):
            "Performs BFS (Breadth First Search) from source to target"
            v = {start}
            qd = deque([start])
            o = []
            while qd:
                u = qd.popleft()
                o.append(u)
                for w in g.get(u, []):
                    if w not in v:
                        v.add(w)
                        qd.append(w)
            return o

    """

    return [code_1, code_2, code_3, code_4, code_5]


def embed_documents_and_query(
    queries=None, docs=None, model=None, index=None, retriever=None
):
    documents = docs

    docs_map = {}

    for i in range(len(documents)):
        docs_map[uuid.uuid4().hex] = documents[i]

    # Encode the documents
    documents_embeddings = model.encode(
        documents,
        batch_size=32,
        is_query=False,  # Encoding documents
        show_progress_bar=False,
    )

    print("=== Successfully embedded the documents ===")

    # Add the documents ids and embeddings to the PLAID index
    index.add_documents(
        documents_ids=list(docs_map.keys()),
        documents_embeddings=documents_embeddings,
    )

    print("=== Added document embeddings to index ===")

    # Embed the queries
    queries_embeddings = model.encode(
        queries,
        batch_size=32,
        is_query=True,  # Encoding queries
        show_progress_bar=False,
    )

    print("=== Embedded the input queries ===")

    print("=== --- Running query over the documents --- ===")

    scores = retriever.retrieve(
        queries_embeddings=queries_embeddings,
        k=10,
    )

    print("=== Retrieved the matched documents with respective scores ===")

    return scores, documents_embeddings, docs_map


if __name__ == "__main__":
    import time

    print(" --- ### Starting the retrieval process ### --- ")

    while True:
        time.sleep(10)
        print("hello\n")


"""

#include <stdio.h>
#include <stdlib.h>

char *reader(FILE *f) {
  char *buffer;
  int buffer_size = 2;
  int offset = 0;
  char c;

  // Set size of buffer where characters will be stored
  buffer = malloc(buffer_size);

  while ((c = fgetc(f)), c != '\n' && c != EOF) {

    // Condition to check if buffer has space remaining else we increase the
    // size of buffer to be able to store more characters
    if (offset ==
        buffer_size -
            1) { // -1 for not counting `\0` (string terminator character)
      // Expand the size of buffer 2x times to reduce chances of resizing
      // repeatedly
      buffer_size *= 2;

      // `realloc` allocates a new block of memory and copies old data to new
      // memory block and finally returns a pointer to the new block of memory
      // to work with.
      char *new_buffer = realloc(buffer, buffer_size);

      if (new_buffer == NULL) {
        free(buffer);
        return NULL;
      }

      buffer = new_buffer;
    }

    // Keep adding characters to buffer
    buffer[offset] = c;
    offset++;
  }

  // If at EOF and we read no bytes, free the buffer and
  // return NULL to indicate we're at EOF:
  if (c == EOF && offset == 0) {
    free(buffer);
    return NULL;
  }

  // Trim the size of old buffer as we have space left which is not being used
  // and again resize and make the new buffer fit to the characters read.
  if (offset < buffer_size - 1) {

    char *new_buffer = realloc(buffer, offset + 1);
    // Here offset is most likely at one index above the read characters because
    // in `while` in the final iteration before loop breaks the value of offset
    // is already exceeded by 1 so we only add +1 since index value is ahead by
    // one so in total we get 2 extra bytes spaces just by +1 ing the new memory
    // size and 1 byte space to be used for `\0` string terminator another for
    // `\n` character. (THINK DEEPLY AND RUN AN EXAMPLE TO UNDERSTAND THIS,
    // QUITE INTERESTING TBH!!!)

    // if we do get a NULL then we leave the old buffer as it is and no need to
    // call free() as it will erase the stored characters
    if (new_buffer != NULL) {
      buffer = new_buffer;
    }
  }

  // Add \n as N-1 character and string terminator as last character in read
  // stream
  buffer[offset] = '\n';
  buffer[offset + 1] = '\0';
  return buffer;
}

int main(void) {
  FILE *f = fopen("./pointers4_example.txt", "r");
  char *line;

  // fgetc automatically tracks the file location using the internal file
  // pointer in the FILE object. So, that means on every reader() func call
  // we continue reading sream where last while condition stopped because of a
  // newline character `\n` encountered.
  while ((line = reader(f)) != NULL) {
    printf("%s", line);
    free(line); // This frees up the buffer memory that is being used to store
                // read stream for current iteration
  }
  fclose(f);
}



"""
