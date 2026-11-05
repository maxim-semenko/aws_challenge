package com.scnsoft.max.aws_challenge.user;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserSyncService {

    private final AppUserRepository repository;

    /** Insert or update the user row for a Cognito user (idempotent: Cognito may retry the trigger). */
    @Transactional
    public AppUser upsert(String cognitoSub, String email, String username) {
        AppUser user = repository.findByCognitoSub(cognitoSub).orElseGet(AppUser::new);
        boolean created = user.getId() == null;

        user.setCognitoSub(cognitoSub);
        user.setEmail(email);
        user.setUsername(username);
        user.setUpdatedAt(Instant.now());

        AppUser saved = repository.save(user);
        log.info("User {} in DB: id={}, sub={}", created ? "created" : "updated", saved.getId(), cognitoSub);
        return saved;
    }
}
