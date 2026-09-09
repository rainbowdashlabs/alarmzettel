{ pkgs ? import <nixpkgs> {}, ... }:

let
  python = pkgs.python314.withPackages (ps: with ps; [
    fastapi
    uvicorn
    pydantic-settings
    python-multipart
    httpx
    segno
  ]);
in
pkgs.mkShell
{
  packages = with pkgs; [nodejs_24 python typst poppler-utils];
}
