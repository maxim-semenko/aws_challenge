package com.scnsoft.max.aws_challenge.security;

import com.amazonaws.serverless.proxy.RequestReader;
import com.amazonaws.serverless.proxy.model.HttpApiV2JwtAuthorizer;
import com.amazonaws.serverless.proxy.model.HttpApiV2ProxyRequestContext;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.util.Arrays;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Reads JWT claims that the API Gateway HTTP API JWT authorizer put into the request context.
 * The token signature/expiry is verified by API Gateway, so the Lambda only reads the claims.
 * <p>
 * Locally there is no API Gateway: with {@code app.auth.dev-user-enabled=true} (profile "local")
 * a fake admin user is returned instead.
 */
@Component
public class CurrentUserResolver {

    private static final CurrentUser DEV_USER =
            new CurrentUser("local-dev-user", "dev@example.com", Set.of(CurrentUser.ADMIN_GROUP));

    private final boolean devUserEnabled;

    public CurrentUserResolver(@Value("${app.auth.dev-user-enabled:false}") boolean devUserEnabled) {
        this.devUserEnabled = devUserEnabled;
    }

    public Optional<CurrentUser> resolve(HttpServletRequest request) {
        if (request.getAttribute(RequestReader.HTTP_API_CONTEXT_PROPERTY) instanceof HttpApiV2ProxyRequestContext ctx
                && ctx.getAuthorizer() != null && ctx.getAuthorizer().isJwt()) {
            HttpApiV2JwtAuthorizer jwt = ctx.getAuthorizer().getJwtAuthorizer();
            Map<String, String> claims = jwt.getClaims();
            return Optional.of(new CurrentUser(claims.get("sub"), claims.get("email"), parseGroups(claims.get("cognito:groups"))));
        }
        return devUserEnabled ? Optional.of(DEV_USER) : Optional.empty();
    }

    public CurrentUser require(HttpServletRequest request) {
        return resolve(request).orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));
    }

    public CurrentUser requireAdmin(HttpServletRequest request) {
        CurrentUser user = require(request);
        if (!user.isAdmin()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Admin group required");
        }
        return user;
    }

    /** HTTP API flattens array claims into a string like "[admin user]". */
    static Set<String> parseGroups(String raw) {
        if (raw == null || raw.isBlank()) {
            return Set.of();
        }
        return Arrays.stream(raw.replace("[", "").replace("]", "").split("[\\s,]+"))
                .filter(s -> !s.isBlank())
                .collect(Collectors.toUnmodifiableSet());
    }
}
