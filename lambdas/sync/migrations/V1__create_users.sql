-- V1: users table, copy of confirmed Cognito users (spec 06 §Outputs is the single home of the column list).
-- PostgreSQL 14 syntax only (R-14). No CHECK constraints, no unique constraint on email, no other index.
CREATE TABLE users (
    id           uuid        NOT NULL PRIMARY KEY,
    email        text        NOT NULL,
    given_name   text,
    family_name  text,
    gender       text,
    birthdate    date,
    country      text,
    height_cm    integer,
    weight_kg    integer,
    confirmed_at timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);
