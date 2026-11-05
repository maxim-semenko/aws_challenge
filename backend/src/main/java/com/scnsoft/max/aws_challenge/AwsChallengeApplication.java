package com.scnsoft.max.aws_challenge;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class AwsChallengeApplication {

    public static void main(String[] args) {
        SpringApplication.run(AwsChallengeApplication.class, args);
    }

}
