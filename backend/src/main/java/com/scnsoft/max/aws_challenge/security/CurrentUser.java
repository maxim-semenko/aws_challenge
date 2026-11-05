package com.scnsoft.max.aws_challenge.security;

import java.util.Set;

/** The caller, as described by the Cognito JWT that API Gateway has already validated. */
public record CurrentUser(String sub, String email, Set<String> groups) {

    public static final String ADMIN_GROUP = "admin";

    public boolean isAdmin() {
        return groups.contains(ADMIN_GROUP);
    }
}
