package com.scnsoft.max.aws_challenge.document;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface DocumentRepository extends JpaRepository<Document, Long> {

    /**
     * k-NN search by cosine distance ({@code <=>}); uses the HNSW index from V1__init.sql.
     *
     * @param embedding vector literal, e.g. "[0.12,-0.03,...]" (see {@link #toVectorLiteral(float[])})
     */
    @Query(value = """
            SELECT d.id AS id, d.title AS title, d.content AS content,
                   d.embedding <=> CAST(:embedding AS vector) AS distance
            FROM document d
            WHERE d.embedding IS NOT NULL
            ORDER BY d.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """, nativeQuery = true)
    List<DocumentSearchResult> findNearest(@Param("embedding") String embedding, @Param("limit") int limit);

    static String toVectorLiteral(float[] vector) {
        StringBuilder sb = new StringBuilder(vector.length * 10).append('[');
        for (int i = 0; i < vector.length; i++) {
            if (i > 0) sb.append(',');
            sb.append(vector[i]);
        }
        return sb.append(']').toString();
    }
}
