MATCH ()-[r]->()
RETURN count(r) AS relationships;