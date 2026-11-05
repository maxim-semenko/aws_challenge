package com.scnsoft.max.aws_challenge.document;

/** Projection for {@link DocumentRepository#findNearest}. Smaller distance = more similar. */
public interface DocumentSearchResult {

    Long getId();

    String getTitle();

    String getContent();

    Double getDistance();
}
