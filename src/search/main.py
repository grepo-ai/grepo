import uuid


def initiate_pylate():
    from pylate import indexes, models, retrieve

    hf_model = "Alibaba-NLP/gte-modernbert-base"
    model = models.ColBERT(
        model_name_or_path=hf_model, document_length=8192, embedding_size=768
    )
    print("=== Loaded model successfully ===")

    index = indexes.PLAID(
        index_folder="pylate-indexes",
        index_name="dino_repo_index",
        override=True,
        centroid_score_threshold=0.70,
        ncells=16,
        embedding_size=768,
    )
    retriever = retrieve.ColBERT(index=index)
    print("=== Created Index successfully a ===")
    return model, retriever, index


def load_data():
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
           \\\"""
           Performs Breadth-First Search (BFS) traversal on a graph from a given start node.

           Parameters:
               g (dict): Adjacency list representation of the graph.
                         Keys are nodes; values are lists of neighboring nodes.
               start: The starting node for BFS traversal.

           Returns:
               list: List of nodes in the order they are visited during BFS traversal.
           \\\"""
           v = {start}            # Set to keep track of visited nodes to avoid revisits (ensures O(1) lookup)
           qd = deque([start])    # Double-ended queue initialized with the start node (FIFO queue for BFS)
           o = []                 # Output list to record the order of BFS traversal

           while qd:
               u = qd.popleft()   # Dequeue the front node for processing
               o.append(u)        # Record the visited node

               for w in g.get(u, []):  # Get neighbors of the current node `u`; default to empty list if `u` not in graph
                   if w not in v:      # If neighbor `w` is not visited
                       v.add(w)        # Mark `w` as visited
                       qd.append(w)    # Enqueue `w` for future processing

           return o  # Final BFS traversal order

    """

    code_5 = """
    class Hello:
        def __init__(self, a, b):
            self.a = a
            self.b = b

        def hello_world(self):
            return "Hello world"


    hey = Hello()
    hey.hello_world()
    """

    code_6 = """

    def menu(death_count):
        global points
        run = True
        while run:
            SCREEN.fill((255, 255, 255))
            font = pygame.font.Font("freesansbold.ttf", 30)

            if death_count == 0:
                text = font.render("Press any Key to Start", True, (0, 0, 0))
            elif death_count > 0:
                text = font.render("Press any Key to Restart", True, (0, 0, 0))
                score = font.render("Your Score: " + str(points), True, (0, 0, 0))
                scoreRect = score.get_rect()
                scoreRect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)
                SCREEN.blit(score, scoreRect)
            textRect = text.get_rect()
            textRect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            SCREEN.blit(text, textRect)
            SCREEN.blit(RUNNING[0], (SCREEN_WIDTH // 2 - 20, SCREEN_HEIGHT // 2 - 140))
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    run = False
                if event.type == pygame.KEYDOWN:
                    main()


    menu(death_count=0)

    """

    code_7 = """

        class Cloud:
            def __init__(self):
                self.x = SCREEN_WIDTH + random.randint(800, 1000)
                self.y = random.randint(50, 100)
                self.image = CLOUD
                self.width = self.image.get_width()

            def update(self):
                self.x -= game_speed
                if self.x < -self.width:
                    self.x = SCREEN_WIDTH + random.randint(2500, 3000)
                    self.y = random.randint(50, 100)

            def draw(self, SCREEN):
                SCREEN.blit(self.image, (self.x, self.y))


    """

    return [code_1, code_2, code_3, code_4, code_5, code_6, code_7]


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
        k=5,
    )

    print("=== Retrieved the matched documents with respective scores ===")

    return scores, queries_embeddings, documents_embeddings, docs_map


def rerank(scores, queries_embeddings, documents_embeddings, docs_map):
    ranked_resp = {}
    return ranked_resp


if __name__ == "__main__":
    print(" --- ### Starting the retrieval process ### --- ")
    import time

    while True:
        time.sleep(10)

    data_docs = load_data()
    model, retriever, index = initiate_pylate()

    scores, queries_embeddings, documents_embeddings, docs_map = (
        embed_documents_and_query(
            queries=["cloud class"],
            docs=data_docs,
            model=model,
            index=index,
            retriever=retriever,
        )
    )
