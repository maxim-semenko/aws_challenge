package com.scnsoft.max.aws_challenge;

import com.scnsoft.max.aws_challenge.user.AppUser;
import com.scnsoft.max.aws_challenge.user.UserSyncService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Import(TestcontainersConfiguration.class)
class AwsChallengeApplicationTests {

    @Autowired
    UserSyncService userSyncService;

    @Test
    void contextLoadsAndMigrationsApply() {
        // Flyway has run V1 (pgvector extension, tables, HNSW index) if the context started
    }

    @Test
    void userSyncIsIdempotent() {
        AppUser first = userSyncService.upsert("sub-123", "a@example.com", "alice");
        AppUser second = userSyncService.upsert("sub-123", "a+new@example.com", "alice");

        assertThat(second.getId()).isEqualTo(first.getId());
        assertThat(second.getEmail()).isEqualTo("a+new@example.com");
    }
}
